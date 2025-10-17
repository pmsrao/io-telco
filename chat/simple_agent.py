"""
Simple Agent wrapper for the existing MCP-based agent
Supports both stdio MCP and HTTP MCP
"""

import asyncio
import os
import subprocess
import sys
import time
import re
import logging
import httpx
import json
from typing import Optional

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from monitoring import get_metrics_collector

# Set up focused logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimpleAgent:
    """Wrapper for the existing MCP-based agent"""
    
    def __init__(self, api_base: str = None, api_key: str = None, use_http_mcp: bool = False):
        """
        Initialize the simple agent
        
        Args:
            api_base: Base URL for the GraphQL API
            api_key: API key for authentication
            use_http_mcp: Whether to use HTTP MCP server instead of stdio MCP
        """
        self.api_base = api_base or os.getenv("TELECOM_API_BASE", "http://localhost:8000")
        self.api_key = api_key or os.getenv("TELECOM_API_KEY", "dev-key")
        self.use_http_mcp = use_http_mcp
        self.mcp_http_base = os.getenv("MCP_HTTP_BASE", "http://localhost:8001")
        self.metrics_collector = get_metrics_collector()
    
    def process_query(self, user_input: str) -> str:
        """
        Process a user query using the existing MCP agent
        
        Args:
            user_input: The user's natural language request
        
        Returns:
            A formatted response
        """
        # Start metrics collection for simple agent
        query_id = self.metrics_collector.start_query(user_input, "simple")
        
        try:
            print(f"🤖 Simple Agent processing: {user_input}")
            print("=" * 60)
            
            # Detect entities in the query
            entities = self._detect_entities(user_input)
            self.metrics_collector.record_entities_detected(query_id, entities)
            
            # Set up environment variables for the MCP agent
            env = os.environ.copy()
            if self.api_base:
                env['TELECOM_API_BASE'] = self.api_base
            if self.api_key:
                env['TELECOM_API_KEY'] = self.api_key
            
            # Record MCP server call
            self.metrics_collector.record_tool_call(query_id)
            
            # Log the intent
            logger.info(f"🎯 INTENT: {user_input}")
            
            cmd = [
                sys.executable, 
                os.path.join(os.path.dirname(__file__), 'agent.py'),
                '--server', 'mcp_server/server.py',
                '--ask', user_input
            ]
            
            # Run the existing agent script
            start_time = time.time()
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                env=env,
                cwd=os.path.dirname(os.path.dirname(__file__))
            )
            execution_time = time.time() - start_time
            
            if result.returncode == 0:
                response = result.stdout.strip()
                print("=" * 60)
                print("✅ Simple Agent completed")
                
                # Extract and log the final GraphQL query
                graphql_queries = self._extract_graphql_queries(result.stdout)
                if graphql_queries:
                    logger.info(f"📝 FINAL GraphQL Query: {graphql_queries[0]}")
                else:
                    logger.info(f"📝 FINAL GraphQL Query: (extracted from output)")
                
                # Count GraphQL queries in the response
                graphql_count = len(graphql_queries) if graphql_queries else self._count_graphql_queries(result.stdout)
                for _ in range(graphql_count):
                    self.metrics_collector.record_graphql_query(query_id)
                
                # Record successful completion
                self.metrics_collector.finish_query(
                    query_id, 
                    success=True, 
                    result_size_bytes=len(response)
                )
                
                return response
            else:
                error_msg = f"❌ Error in Simple Agent: {result.stderr}"
                print(error_msg)
                
                # Record failed completion
                self.metrics_collector.finish_query(
                    query_id, 
                    success=False, 
                    error_type="SubprocessError", 
                    error_message=result.stderr
                )
                
                return error_msg
                
        except Exception as e:
            error_msg = f"❌ Error in Simple Agent: {str(e)}"
            print(error_msg)
            
            # Record failed completion
            self.metrics_collector.finish_query(
                query_id, 
                success=False, 
                error_type=type(e).__name__, 
                error_message=str(e)
            )
            
            return error_msg
    
    def _detect_entities(self, query_text: str) -> list:
        """Detect entities mentioned in the query"""
        query_lower = query_text.lower()
        entities = []
        
        if any(word in query_lower for word in ['payment', 'payments']):
            entities.append('payments')
        if any(word in query_lower for word in ['bill', 'bills']):
            entities.append('bills')
        if any(word in query_lower for word in ['customer', 'customers']):
            entities.append('customers')
        if any(word in query_lower for word in ['subscription', 'subscriptions']):
            entities.append('subscriptions')
        if any(word in query_lower for word in ['account', 'accounts']):
            entities.append('accounts')
        
        return entities
    
    def _extract_graphql_queries(self, output_text: str) -> list:
        """Extract GraphQL queries from the output"""
        queries = []
        
        # Look for complete GraphQL queries
        query_pattern = r'query\s+\w+\s*\([^)]*\)\s*\{[^}]+\}'
        matches = re.findall(query_pattern, output_text, re.IGNORECASE | re.DOTALL)
        queries.extend(matches)
        
        # Look for GraphQL query fragments
        fragment_pattern = r'\{[^}]*list_\w+[^}]*\}'
        fragment_matches = re.findall(fragment_pattern, output_text, re.IGNORECASE | re.DOTALL)
        queries.extend(fragment_matches)
        
        return queries
    
    def _count_graphql_queries(self, output_text: str) -> int:
        """Count GraphQL queries in the output"""
        queries = self._extract_graphql_queries(output_text)
        return len(queries) if queries else 1  # At least 1 query if we got a response
