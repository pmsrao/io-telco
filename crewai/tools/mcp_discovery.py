"""
MCP Discovery Tools for CrewAI
Provides tools to discover data products and contracts via MCP
"""

import json
import httpx
from crewai_tools import BaseTool
from typing import Dict, Any, List


class MCPDiscoveryTool(BaseTool):
    name: str = "mcp_discovery"
    description: str = "Discover available data products and their contracts via MCP"
    
    def __init__(self, mcp_base_url: str = "http://localhost:8000"):
        super().__init__()
        self.mcp_base_url = mcp_base_url
    
    def _run(self, action: str = "discover_products") -> str:
        """
        Discover data products and contracts
        
        Args:
            action: The discovery action to perform
                   - "discover_products": Get list of all data products
                   - "get_contract": Get contract for specific product (requires product param)
        
        Returns:
            JSON string with discovery results
        """
        try:
            if action == "discover_products":
                return self._discover_products()
            elif action == "get_contract":
                return self._get_contract()
            else:
                return json.dumps({"error": f"Unknown action: {action}"})
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    def _discover_products(self) -> str:
        """Get list of all available data products"""
        url = f"{self.mcp_base_url}/.well-known/telecom.registry.index"
        
        with httpx.Client() as client:
            response = client.get(url, timeout=30.0)
            response.raise_for_status()
            return json.dumps(response.json())
    
    def _get_contract(self, product: str) -> str:
        """Get contract details for a specific data product"""
        url = f"{self.mcp_base_url}/.well-known/telecom.registry/{product}.yaml"
        
        with httpx.Client() as client:
            response = client.get(url, timeout=30.0)
            response.raise_for_status()
            return json.dumps(response.json())


class MCPContractTool(BaseTool):
    name: str = "mcp_contract"
    description: str = "Get contract details for a specific data product"
    
    def __init__(self, mcp_base_url: str = "http://localhost:8000"):
        super().__init__()
        self.mcp_base_url = mcp_base_url
    
    def _run(self, product: str) -> str:
        """
        Get contract details for a specific data product
        
        Args:
            product: The data product name (e.g., 'payments', 'customer')
        
        Returns:
            JSON string with contract details
        """
        try:
            url = f"{self.mcp_base_url}/.well-known/telecom.registry/{product}.yaml"
            
            with httpx.Client() as client:
                response = client.get(url, timeout=30.0)
                response.raise_for_status()
                return json.dumps(response.json())
        except Exception as e:
            return json.dumps({"error": str(e)})


class MCPSchemaTool(BaseTool):
    name: str = "mcp_schema"
    description: str = "Get the complete GraphQL schema for all data products"
    
    def __init__(self, mcp_base_url: str = "http://localhost:8000"):
        super().__init__()
        self.mcp_base_url = mcp_base_url
    
    def _run(self) -> str:
        """
        Get the complete GraphQL schema
        
        Returns:
            GraphQL SDL string
        """
        try:
            url = f"{self.mcp_base_url}/.well-known/telecom.graphql.sdl"
            
            with httpx.Client() as client:
                response = client.get(url, timeout=30.0)
                response.raise_for_status()
                return response.text
        except Exception as e:
            return json.dumps({"error": str(e)})
