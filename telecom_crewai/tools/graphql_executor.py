"""
GraphQL Executor Tool for CrewAI
Executes GraphQL queries against the telecom API
"""

import json
import httpx
from crewai.tools import BaseTool
from typing import Dict, Any


class GraphQLExecutorTool(BaseTool):
    name: str = "graphql_executor"
    description: str = "Execute GraphQL queries against the telecom API"
    api_base: str = "http://localhost:8000"
    api_key: str = "dev-key"
    
    def __init__(self, api_base: str = "http://localhost:8000", api_key: str = "dev-key", **kwargs):
        super().__init__(**kwargs)
        self.api_base = api_base
        self.api_key = api_key
    
    def _run(self, query: str, variables: Dict[str, Any] = None) -> str:
        """
        Execute a GraphQL query
        
        Args:
            query: The GraphQL query string
            variables: Optional variables for the query
        
        Returns:
            JSON string with the query results
        """
        try:
            url = f"{self.api_base}/graphql"
            payload = {
                "query": query,
                "variables": variables or {}
            }
            headers = {
                "x-api-key": self.api_key,
                "Content-Type": "application/json"
            }
            
            with httpx.Client() as client:
                response = client.post(url, headers=headers, json=payload, timeout=60.0)
                response.raise_for_status()
                
                result = response.json()
                
                # Log the execution
                print(f"GraphQL Query Executed:")
                print(f"Query: {query}")
                print(f"Variables: {json.dumps(variables or {}, indent=2)}")
                print(f"Result: {json.dumps(result, indent=2)}")
                
                return json.dumps(result)
                
        except Exception as e:
            error_result = {
                "error": str(e),
                "query": query,
                "variables": variables
            }
            return json.dumps(error_result)
