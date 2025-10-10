import os
import json
import asyncio

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER = os.environ.get(
    "MCP_SERVER",
    "/Users/madhu.p/madhu_podila/work/projects/j2/mcp_server/server.py",
)

QUERY = """
query($acct:String!,$from:String!,$to:String!){
  list_payments(
    filters:{ account_id:$acct, status:"POSTED", from_time:$from, to_time:$to },
    limit:20
  ){
    payment_id amount currency status created_at
  }
}
"""

VARS = {
  "acct": "ACC-1002",
  "from": "2025-09-08T00:00:00Z",
  "to":   "2025-10-08T23:59:59Z"
}

def normalize_tool_content(resp):
    """
    Convert FastMCP tool response to a plain dict.
    Handles:
      - list of TextContent objects (resp.content: [TextContent(...), ...])
      - list of dicts with "text"
      - raw str
      - raw dict
    """
    content = getattr(resp, "content", resp)

    # If it's a list of content blocks, concatenate all text parts.
    if isinstance(content, list):
        parts = []
        for c in content:
            # TextContent from MCP SDK
            if hasattr(c, "text"):
                parts.append(c.text)
            # dict-ish fallback
            elif isinstance(c, dict) and "text" in c:
                parts.append(c["text"])
        text = "\n".join(parts).strip()
        if text:
            try:
                return json.loads(text)  # server returned JSON text
            except Exception:
                return {"text": text}    # plain text
        # nothing to stringify: just show repr
        return {"raw": [repr(c) for c in content]}

    # If it’s a raw string, try JSON first
    if isinstance(content, str):
        try:
            return json.loads(content)
        except Exception:
            return {"text": content}

    # If it’s already a dict, return as-is
    if isinstance(content, dict):
        return content

    # Last resort
    return {"raw": repr(content)}

async def main():
    params = StdioServerParameters(
        command="python",
        args=[SERVER],
        env={
            "TELECOM_API_BASE": os.getenv("TELECOM_API_BASE","http://localhost:8080"),
            "TELECOM_GQL_PATH": os.getenv("TELECOM_GQL_PATH","/graphql"),
            "TELECOM_API_KEY":  os.getenv("TELECOM_API_KEY","dev-key"),
        },
    )

    # stdio_client is an async context manager
    async with stdio_client(params) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()

            resp = await session.call_tool(
                "telecom.graphql.run",
                {"query": QUERY, "variables": VARS},
            )

            out = normalize_tool_content(resp)
            print(json.dumps(out, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
