#!/usr/bin/env python3
# chat/agent.py
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, Tuple

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from dotenv import load_dotenv
load_dotenv()


# ------------------------- UTC time helpers -------------------------

def compute_window_from_text(text: str) -> Tuple[str, str]:
    """
    Very small parser: "last N days" -> [now- N days @00:00Z, now @23:59:59Z]
    Defaults to 90 days to include more historical data.
    """
    m = re.search(r"last\s+(\d+)\s*days?", text, re.I)
    days = int(m.group(1)) if m else 90  # Increased from 30 to 90 days
    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)
    end = now.replace(microsecond=0)
    # Format timestamps to match database format: "YYYY-MM-DDTHH:MM:SS.000+00:00"
    start_str = start.strftime("%Y-%m-%dT%H:%M:%S.000+00:00")
    end_str = end.strftime("%Y-%m-%dT%H:%M:%S.000+00:00")
    return start_str, end_str


# ------------------------- Simple intent → GraphQL builder -------------------------

ACC_RE = re.compile(r"\bACC-\d+\b", re.I)
BILL_RE = re.compile(r"\bBILL-\d+\b", re.I)

def nl_to_tool_call(text: str) -> Dict[str, Any]:
    """
    Very small intent router for your two common cases.
    Falls back to a generic payments list if nothing matches.
    """
    frm, to = compute_window_from_text(text)
    acc = ACC_RE.search(text or "") and ACC_RE.search(text).group(0)
    bill = BILL_RE.search(text or "") and BILL_RE.search(text).group(0)

    # Case A: "show POSTED payments for ACC-XXXX in the last 30 days"
    if acc:
        return {
            "tool": "telecom.graphql.run",
            "query": (
                "query($acct:String!,$from:String!,$to:String!){ "
                "  list_payments(filters:{ account_id:$acct, status:\"POSTED\", from_time:$from, to_time:$to }, limit:50){ "
                "    payment_id amount currency status created_at "
                "  } "
                "}"
            ),
            "variables": {"acct": acc, "from": frm, "to": to},
        }

    # Case B: "get bill BILL-XXXX and list its payments"
    if bill:
        # Your schema DOES have payments.bill_id, so prefer single-call with bill_id filter:
        return {
            "tool": "telecom.graphql.run",
            "query": (
                "query($bill:String!,$from:String!,$to:String!){ "
                "  get_bill(key:$bill){ bill_id account_id amount_due status bill_date } "
                "  list_payments(filters:{ bill_id:$bill, from_time:$from, to_time:$to }, limit:50){ "
                "    payment_id amount currency status created_at "
                "  } "
                "}"
            ),
            "variables": {"bill": bill, "from": frm, "to": to},
        }

    # Fallback: last 30 days, all POSTED payments
    return {
        "tool": "telecom.graphql.run",
        "query": (
            "query($from:String!,$to:String!){ "
            "  list_payments(filters:{ status:\"POSTED\", from_time:$from, to_time:$to }, limit:50){ "
            "    payment_id amount currency status created_at "
            "  } "
            "}"
        ),
        "variables": {"from": frm, "to": to},
    }


# ------------------------- Sanitizer (requested) -------------------------

CODE_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.S)

def strip_code_fences(t: str) -> str:
    return CODE_FENCE_RE.sub("", t or "")

def fix_common_escapes(t: str) -> str:
    # undo double-escaped quotes that LLMs sometimes emit
    return (t or "").replace('\\\\"', '\\"')

def rewrite_bill_id_in_payments(query: str) -> str:
    """
    If the SAME operation contains `get_bill(key:$X)` and also `list_payments(... filters:{ account_id:$X ...})`,
    rewrite that filter to `bill_id:$X`.
    """
    m = re.search(r'get_?bill\s*\(\s*key\s*:\s*\$([A-Za-z_][A-Za-z0-9_]*)', query)
    if not m:
        return query
    var = m.group(1)
    pattern = rf'(list_payments\s*\(\s*[^)]*filters\s*:\s*\{{[^}}]*?)account_id\s*:\s*\${var}'
    repl = r'\1bill_id:$' + var
    return re.sub(pattern, repl, query)

def ensure_variables_dict(obj: Dict[str, Any]) -> None:
    if "variables" not in obj or obj["variables"] is None:
        obj["variables"] = {}

def sanitize_tool_call(raw: str) -> Dict[str, Any]:
    """
    Accepts a model-produced or hand-composed JSON-ish string and returns a dict
    with safe `tool`, `query`, `variables`.
    Also performs the requested bill_id/account_id rewrite.
    """
    s = fix_common_escapes(strip_code_fences(raw))
    try:
        obj = json.loads(s)
    except Exception:
        # If not JSON (e.g., plain GraphQL), wrap it as a tool call
        obj = {"tool": "telecom.graphql.run", "query": s, "variables": {}}

    # Normalize expected shape
    obj["tool"] = obj.get("tool") or "telecom.graphql.run"
    q = obj.get("query") or ""
    q = rewrite_bill_id_in_payments(q)
    obj["query"] = q
    ensure_variables_dict(obj)

    # Log sanitized query preview
    preview = q.replace("\n", " ")
    if len(preview) > 400:
        preview = preview[:400] + "…"
    print(f"SANITIZED QUERY => {preview}")
    return obj


# ------------------------- MCP Session wrapper -------------------------

class TelecomMCPClient:
    def __init__(self, server_script: str, server_env: Optional[Dict[str, str]] = None):
        self.server_script = server_script
        self.server_env = server_env or os.environ.copy()
        self.session: Optional[ClientSession] = None
        self._ctx = None

    async def __aenter__(self):
        # Start the MCP server via stdio
        params = StdioServerParameters(
            command=os.environ.get("PYTHON", "python"),
            args=[self.server_script],
            env=self.server_env,
        )
        self._ctx = stdio_client(params)
        self.reader, self.writer = await self._ctx.__aenter__()
        self.session = ClientSession(self.reader, self.writer)
        await self.session.__aenter__()
        await self.session.initialize()
        # optional: list tools (helps verify connection)
        await self.session.list_tools()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        try:
            if self.session:
                await self.session.__aexit__(exc_type, exc, tb)
        finally:
            if self._ctx:
                await self._ctx.__aexit__(exc_type, exc, tb)

    async def call_graphql(self, query: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call the telecom.graphql.run tool. The MCP server injects the API key and endpoint.
        """
        assert self.session, "MCP session not initialized"
        tool_name = "telecom.graphql.run"
        args = {"query": query, "variables": variables}
        # Optional log of window if present
        frm = variables.get("from")
        to = variables.get("to")
        if frm and to:
            print(f"Executing tool with window: {frm} → {to}")

        result = await self.session.call_tool(tool_name, args)
        # server returns a single TextContent item with JSON body
        content = result.content[0].text if result.content else ""
        try:
            data = json.loads(content)
        except Exception:
            data = {"raw": content}
        print(json.dumps(data, indent=2))
        return data


# ------------------------- Chat loop / one-shot -------------------------

async def chat_once(server_script: str, user_text: str):
    # Build a tool call from NL (lightweight rules). If you prefer an LLM, you can
    # replace this with a model request and then feed it through sanitize_tool_call().
    tc = nl_to_tool_call(user_text)

    # Sanitize (and apply the bill_id/account_id rewrite if needed)
    tc = sanitize_tool_call(json.dumps(tc))

    server_env = os.environ.copy()  # TELECOM_API_* should be set outside (Makefile)
    async with TelecomMCPClient(server_script, server_env) as client:
        await client.call_graphql(tc["query"], tc.get("variables", {}))


async def interactive_loop(server_script: str):
    print("telecom-chat (MCP) — type 'exit' to quit")
    while True:
        try:
            q = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not q or q.lower() in {"exit", "quit"}:
            break
        await chat_once(server_script, q)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", default="mcp_server/server.py", help="Path to MCP server.py")
    ap.add_argument("--ask", help="One-shot prompt (otherwise interactive)")
    args = ap.parse_args()

    if args.ask:
        asyncio.run(chat_once(args.server, args.ask))
    else:
        asyncio.run(interactive_loop(args.server))


if __name__ == "__main__":
    main()
