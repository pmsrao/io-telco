"""
HTTP MCP Tools for CrewAI
These tools communicate with the HTTP MCP server instead of stdio MCP
"""

import asyncio
import json
import httpx
import os
from typing import Dict, Any, Optional
from crewai.tools import BaseTool


class HTTPMCPDiscoveryTool(BaseTool):
    """Tool for discovering data products via HTTP MCP server"""
    
    name: str = "mcp_discovery"
    description: str = "Discover available data products and their contracts via HTTP MCP"
    api_base: str = "http://localhost:8000"
    mcp_http_base: str = "http://localhost:8001"
    
    def __init__(self, api_base: str = "http://localhost:8000", **kwargs):
        super().__init__(**kwargs)
        self.api_base = api_base
        self.mcp_http_base = os.getenv("MCP_HTTP_BASE", "http://localhost:8001")
    
    def _run(self, **kwargs) -> str:
        """Run the discovery tool via HTTP MCP"""
        return asyncio.run(self._discover_products())
    
    async def _discover_products(self) -> str:
        """Discover products via HTTP MCP server"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.mcp_http_base}/tools/execute",
                    json={
                        "tool_name": "telecom.discover.products",
                        "arguments": {}
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                result = response.json()
                return result.get("result", "{}")
        except Exception as e:
            return f"Error discovering products: {str(e)}"


class HTTPMCPContractTool(BaseTool):
    """Tool for getting contract details via HTTP MCP server"""
    
    name: str = "mcp_contract"
    description: str = "Get contract details for a specific data product via HTTP MCP"
    api_base: str = "http://localhost:8000"
    mcp_http_base: str = "http://localhost:8001"
    
    def __init__(self, api_base: str = "http://localhost:8000", **kwargs):
        super().__init__(**kwargs)
        self.api_base = api_base
        self.mcp_http_base = os.getenv("MCP_HTTP_BASE", "http://localhost:8001")
    
    def _run(self, product: str, **kwargs) -> str:
        """Run the contract tool via HTTP MCP"""
        return asyncio.run(self._get_contract(product))
    
    async def _get_contract(self, product: str) -> str:
        """Get contract via HTTP MCP server"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.mcp_http_base}/tools/execute",
                    json={
                        "tool_name": "telecom.contract.get",
                        "arguments": {"product": product}
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                result = response.json()
                return result.get("result", "{}")
        except Exception as e:
            return f"Error getting contract for {product}: {str(e)}"


class HTTPMCPSchemaTool(BaseTool):
    """Tool for getting GraphQL schema via HTTP MCP server"""
    
    name: str = "mcp_schema"
    description: str = "Get GraphQL schema details via HTTP MCP"
    api_base: str = "http://localhost:8000"
    mcp_http_base: str = "http://localhost:8001"
    
    def __init__(self, api_base: str = "http://localhost:8000", **kwargs):
        super().__init__(**kwargs)
        self.api_base = api_base
        self.mcp_http_base = os.getenv("MCP_HTTP_BASE", "http://localhost:8001")
    
    def _run(self, **kwargs) -> str:
        """Run the schema tool via HTTP MCP"""
        return asyncio.run(self._get_schema())
    
    async def _get_schema(self) -> str:
        """Get schema via HTTP MCP server"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.mcp_http_base}/tools/execute",
                    json={
                        "tool_name": "telecom.schema.get",
                        "arguments": {}
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                result = response.json()
                return result.get("result", "{}")
        except Exception as e:
            return f"Error getting schema: {str(e)}"


class HTTPMCPGraphQLExecutorTool(BaseTool):
    """Tool for executing GraphQL queries via HTTP MCP server"""
    
    name: str = "graphql_executor"
    description: str = "Execute GraphQL queries via HTTP MCP server"
    api_base: str = "http://localhost:8000"
    api_key: str = "dev-key"
    mcp_http_base: str = "http://localhost:8001"
    
    def __init__(self, api_base: str = "http://localhost:8000", api_key: str = "dev-key", **kwargs):
        super().__init__(**kwargs)
        self.api_base = api_base
        self.api_key = api_key
        self.mcp_http_base = os.getenv("MCP_HTTP_BASE", "http://localhost:8001")
    
    def _run(self, query: str, variables: Optional[Dict[str, Any]] = None, **kwargs) -> str:
        """Run GraphQL query via HTTP MCP"""
        return asyncio.run(self._execute_graphql(query, variables or {}))
    
    async def _execute_graphql(self, query: str, variables: Dict[str, Any]) -> str:
        """Execute GraphQL query via HTTP MCP server"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.mcp_http_base}/tools/execute",
                    json={
                        "tool_name": "telecom.graphql.run",
                        "arguments": {
                            "query": query,
                            "variables": variables
                        }
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                result = response.json()
                return result.get("result", "{}")
        except Exception as e:
            return f"Error executing GraphQL query: {str(e)}"
