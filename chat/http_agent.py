#!/usr/bin/env python3
"""
HTTP-based Agent for Telecom Data Products
This version connects to the MCP HTTP server instead of using stdio
"""

import argparse
import asyncio
import json
import os
import re
import httpx
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()

# HTTP MCP Server configuration
MCP_HTTP_BASE = os.getenv("MCP_HTTP_BASE", "http://localhost:8001")

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
    end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    # Format timestamps to match database expected format
    start_str = start.strftime("%Y-%m-%dT%H:%M:%S.000+00:00")
    end_str = end.strftime("%Y-%m-%dT%H:%M:%S.000+00:00")
    
    return start_str, end_str

# ------------------------- Natural Language to Tool Call -------------------------

def nl_to_tool_call(text: str) -> Dict[str, Any]:
    """
    Convert natural language to a tool call.
    This is a simple rule-based approach - you could replace with an LLM.
    """
    text_lower = text.lower()
    
    # Complex multi-entity queries (check first to avoid false positives)
    if any(word in text_lower for word in ["customer", "customers"]) and any(word in text_lower for word in ["bill", "bills", "payment", "payments"]):
        # Multi-entity query: customers + bills + payments
        return {
            "tool": "telecom.graphql.run",
            "query": """
            query($country:String!,$bill_status:String!,$payment_status:String!,$from:String!,$to:String!) {
                list_customer_profile(filters:{ country:$country }, limit:50) {
                    customer_id full_name country status
                }
                list_bills(filters:{ status:$bill_status, from_date:$from, to_date:$to }, limit:50) {
                    bill_id account_id amount_due status bill_date
                }
                list_payments(filters:{ status:$payment_status, from_time:$from, to_time:$to }, limit:50) {
                    payment_id account_id amount currency status created_at
                }
            }
            """,
            "variables": {
                "country": "IN" if "india" in text_lower else "US",
                "bill_status": "UNPAID" if "unpaid" in text_lower else "PENDING",
                "payment_status": "POSTED",
                "from": compute_window_from_text(text)[0],
                "to": compute_window_from_text(text)[1]
            }
        }
    
    # Bill queries (check before payment to handle "bill and payments")
    elif "bill" in text_lower:
        if "get" in text_lower or "show" in text_lower:
            # Extract bill ID
            bill_match = re.search(r'bill[:\s]+([A-Z0-9-]+)', text, re.I)
            bill_id = bill_match.group(1) if bill_match else "BILL-9001"
            
            return {
                "tool": "telecom.graphql.run",
                "query": """
                query($bill:String!,$from:String!,$to:String!) {
                    get_bill(key:$bill) {
                        bill_id account_id amount_due status bill_date
                    }
                    list_payments(filters:{ bill_id:$bill, from_time:$from, to_time:$to }, limit:50) {
                        payment_id amount currency status created_at
                    }
                }
                """,
                "variables": {
                    "bill": bill_id,
                    "from": compute_window_from_text(text)[0],
                    "to": compute_window_from_text(text)[1]
                }
            }
    
    # Payment queries (check last to avoid false positives)
    elif "payment" in text_lower:
        # Extract account ID from various patterns
        account_match = re.search(r'(?:account[:\s]+|for\s+)([A-Z0-9-]+)', text, re.I)
        if account_match:
            account_id = account_match.group(1)
        elif "account" in text_lower:
            account_match = re.search(r'account[:\s]+([A-Z0-9-]+)', text, re.I)
            account_id = account_match.group(1) if account_match else "ACC-1002"
        else:
            account_id = "ACC-1002"  # default
        
        # Check for status filter
        status = "POSTED"  # default
        if "pending" in text_lower:
            status = "PENDING"
        elif "failed" in text_lower:
            status = "FAILED"
        elif "posted" in text_lower:
            status = "POSTED"
        
        return {
                "tool": "telecom.graphql.run",
                "query": """
                query($acct:String!,$from:String!,$to:String!) {
                    list_payments(filters:{ account_id:$acct, status:"POSTED", from_time:$from, to_time:$to }, limit:50) {
                        payment_id amount currency status created_at
                    }
                }
                """,
                "variables": {
                    "acct": account_id,
                    "from": compute_window_from_text(text)[0],
                    "to": compute_window_from_text(text)[1]
                }
            }
    
    # Bill queries
    elif "bill" in text_lower:
        if "get" in text_lower or "show" in text_lower:
            # Extract bill ID
            bill_match = re.search(r'bill[:\s]+([A-Z0-9-]+)', text, re.I)
            bill_id = bill_match.group(1) if bill_match else "BILL-9001"
            
            return {
                "tool": "telecom.graphql.run",
                "query": """
                query($bill:String!,$from:String!,$to:String!) {
                    get_bill(key:$bill) {
                        bill_id account_id amount_due status bill_date
                    }
                    list_payments(filters:{ bill_id:$bill, from_time:$from, to_time:$to }, limit:50) {
                        payment_id amount currency status created_at
                    }
                }
                """,
                "variables": {
                    "bill": bill_id,
                    "from": compute_window_from_text(text)[0],
                    "to": compute_window_from_text(text)[1]
                }
            }
    
    # Default fallback
    return {
        "tool": "telecom.discover.products",
        "query": "",
        "variables": {}
    }

def sanitize_tool_call(tool_call_json: str) -> Dict[str, Any]:
    """Sanitize and validate tool call JSON"""
    try:
        tc = json.loads(tool_call_json)
        
        # Ensure required fields exist
        if "tool" not in tc:
            tc["tool"] = "telecom.discover.products"
        if "query" not in tc:
            tc["query"] = ""
        if "variables" not in tc:
            tc["variables"] = {}
            
        return tc
    except json.JSONDecodeError:
        # Fallback to discovery
        return {
            "tool": "telecom.discover.products",
            "query": "",
            "variables": {}
        }

# ------------------------- HTTP MCP Client -------------------------

class HTTPMCPClient:
    """HTTP client for MCP server communication"""
    
    def __init__(self, base_url: str = MCP_HTTP_BASE):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc, tb):
        await self.client.aclose()
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Call a tool on the MCP server"""
        try:
            response = await self.client.post(
                f"{self.base_url}/tools/execute",
                json={
                    "tool_name": tool_name,
                    "arguments": arguments or {}
                }
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "result": None
            }
    
    async def discover_products(self) -> Dict[str, Any]:
        """Discover available data products"""
        return await self.call_tool("telecom.discover.products")
    
    async def get_contract(self, product: str) -> Dict[str, Any]:
        """Get contract for a data product"""
        return await self.call_tool("telecom.contract.get", {"product": product})
    
    async def get_schema(self) -> Dict[str, Any]:
        """Get GraphQL schema"""
        return await self.call_tool("telecom.schema.get")
    
    async def run_graphql(self, query: str, variables: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute GraphQL query"""
        return await self.call_tool("telecom.graphql.run", {
            "query": query,
            "variables": variables or {}
        })

# ------------------------- Chat loop / one-shot -------------------------

async def chat_once(user_text: str):
    """Execute a single query"""
    # Build a tool call from NL (lightweight rules)
    tc = nl_to_tool_call(user_text)
    
    # Sanitize the tool call
    tc = sanitize_tool_call(json.dumps(tc))
    
    print(f"SANITIZED QUERY => {tc['query']}")
    print(f"Executing tool with window: {tc['variables'].get('from', 'N/A')} → {tc['variables'].get('to', 'N/A')}")
    
    async with HTTPMCPClient() as client:
        if tc["tool"] == "telecom.graphql.run":
            result = await client.run_graphql(tc["query"], tc.get("variables", {}))
        elif tc["tool"] == "telecom.discover.products":
            result = await client.discover_products()
        elif tc["tool"] == "telecom.contract.get":
            product = tc.get("variables", {}).get("product", "payments")
            result = await client.get_contract(product)
        else:
            result = await client.discover_products()
        
        if result.get("success"):
            print(json.dumps(result["result"], indent=2))
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")

async def interactive_loop():
    """Interactive chat loop"""
    print("telecom-chat (HTTP MCP) — type 'exit' to quit")
    while True:
        try:
            q = input("\n> ")
            if not q or q.lower() in {"exit", "quit"}:
                break
            await chat_once(q)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

def main():
    global MCP_HTTP_BASE
    
    ap = argparse.ArgumentParser()
    ap.add_argument("--ask", help="One-shot prompt (otherwise interactive)")
    ap.add_argument("--mcp-url", default=MCP_HTTP_BASE, help="MCP HTTP server URL")
    args = ap.parse_args()
    
    # Update MCP URL if provided
    MCP_HTTP_BASE = args.mcp_url
    
    if args.ask:
        asyncio.run(chat_once(args.ask))
    else:
        asyncio.run(interactive_loop())

async def execute_tool_call(tool_call: Dict[str, Any], mcp_base: str = None) -> str:
    """Execute a tool call via HTTP MCP server"""
    if mcp_base:
        global MCP_HTTP_BASE
        MCP_HTTP_BASE = mcp_base
    
    # Sanitize the tool call
    tc = sanitize_tool_call(json.dumps(tool_call))
    
    async with HTTPMCPClient() as client:
        if tc["tool"] == "telecom.graphql.run":
            result = await client.run_graphql(tc["query"], tc.get("variables", {}))
        elif tc["tool"] == "telecom.discover.products":
            result = await client.discover_products()
        elif tc["tool"] == "telecom.contract.get":
            product = tc.get("variables", {}).get("product", "payments")
            result = await client.get_contract(product)
        else:
            result = await client.discover_products()
    
    return result

if __name__ == "__main__":
    main()
