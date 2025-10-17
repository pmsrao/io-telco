"""
CrewAI Agent for Telecom Data Product Queries
Provides a high-level interface for complex natural language queries
"""

import os
import sys
import time
import re
import logging
from typing import Optional

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telecom_crewai.crew import TelecomCrew
from monitoring import get_metrics_collector

# Set up focused logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CrewAIAgent:
    """CrewAI-based agent for complex telecom data product queries"""
    
    def __init__(self, api_base: str = None, api_key: str = None, use_http_mcp: bool = False):
        """
        Initialize the CrewAI agent
        
        Args:
            api_base: Base URL for the GraphQL API (defaults to env var)
            api_key: API key for authentication (defaults to env var)
            use_http_mcp: Whether to use HTTP MCP server instead of stdio MCP
        """
        self.api_base = api_base or os.getenv("TELECOM_API_BASE", "http://localhost:8000")
        self.api_key = api_key or os.getenv("TELECOM_API_KEY", "dev-key")
        self.use_http_mcp = use_http_mcp
        self.mcp_http_base = os.getenv("MCP_HTTP_BASE", "http://localhost:8001")
        
        # Initialize the crew
        self.crew = TelecomCrew(self.api_base, self.api_key, use_http_mcp=use_http_mcp)
        self.metrics_collector = get_metrics_collector()
    
    def process_query(self, user_input: str) -> str:
        """
        Process a user query using the CrewAI crew
        
        Args:
            user_input: The user's natural language request
        
        Returns:
            A formatted response
        """
        # Start metrics collection for CrewAI agent
        query_id = self.metrics_collector.start_query(user_input, "crewai")
        
        try:
            print(f"🤖 CrewAI Agent processing: {user_input}")
            print("=" * 60)
            
            # Log the intent
            logger.info(f"🎯 INTENT: {user_input}")
            
            # Detect entities in the query
            entities = self._detect_entities(user_input)
            self.metrics_collector.record_entities_detected(query_id, entities)
            
            # Process through the crew
            start_time = time.time()
            result = self.crew.process_query(user_input)
            execution_time = time.time() - start_time
            
            print("=" * 60)
            print("✅ CrewAI Agent completed")
            
            # Extract and log the final GraphQL query
            graphql_queries = self._extract_graphql_queries(str(result))
            if graphql_queries:
                logger.info(f"📝 FINAL GraphQL Query: {graphql_queries[0]}")
            else:
                logger.info(f"📝 FINAL GraphQL Query: (extracted from output)")
            
            # Count tool calls and GraphQL queries in the result
            tool_calls_count = self._count_tool_calls(result)
            graphql_queries_count = len(graphql_queries) if graphql_queries else self._count_graphql_queries(result)
            
            # Record tool calls and GraphQL queries
            for _ in range(tool_calls_count):
                self.metrics_collector.record_tool_call(query_id)
            for _ in range(graphql_queries_count):
                self.metrics_collector.record_graphql_query(query_id)
            
            # Record successful completion
            self.metrics_collector.finish_query(
                query_id, 
                success=True, 
                result_size_bytes=len(str(result))
            )
            
            return result
            
        except Exception as e:
            error_msg = f"❌ Error in CrewAI Agent: {str(e)}"
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
    
    def _count_tool_calls(self, output_text: str) -> int:
        """Count tool calls in the output"""
        # Look for tool call patterns in CrewAI output
        tool_patterns = [
            r'Using tool:',
            r'Tool call:',
            r'mcp_discovery',
            r'mcp_contract',
            r'mcp_schema',
            r'graphql_query_builder',
            r'graphql_executor',
            r'entity_correlator',
        ]
        
        count = 0
        for pattern in tool_patterns:
            matches = re.findall(pattern, output_text, re.IGNORECASE)
            count += len(matches)
        
        return max(1, count)  # At least 1 tool call if we got a response
    
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
        
        # Look for queries in tool output
        tool_query_pattern = r'GraphQL query:\s*([^}]+)'
        tool_matches = re.findall(tool_query_pattern, output_text, re.IGNORECASE | re.DOTALL)
        queries.extend(tool_matches)
        
        return queries
    
    def _count_graphql_queries(self, output_text: str) -> int:
        """Count GraphQL queries in the output"""
        queries = self._extract_graphql_queries(output_text)
        return len(queries) if queries else 1  # At least 1 query if we got a response
    
    def get_available_products(self) -> str:
        """Get list of available data products"""
        try:
            return self.crew.get_available_products()
        except Exception as e:
            return f"Error getting available products: {str(e)}"
    
    def get_product_contract(self, product: str) -> str:
        """Get contract details for a specific product"""
        try:
            return self.crew.get_product_contract(product)
        except Exception as e:
            return f"Error getting contract for {product}: {str(e)}"


def main():
    """Main function for testing the CrewAI agent"""
    import argparse
    
    parser = argparse.ArgumentParser(description="CrewAI Agent for Telecom Data Products")
    parser.add_argument("--ask", type=str, help="Natural language query to process")
    parser.add_argument("--list-products", action="store_true", help="List available data products")
    parser.add_argument("--get-contract", type=str, help="Get contract for a specific product")
    parser.add_argument("--api-base", type=str, default="http://localhost:8000", help="API base URL")
    parser.add_argument("--api-key", type=str, default="dev-key", help="API key")
    
    args = parser.parse_args()
    
    # Initialize agent
    agent = CrewAIAgent(args.api_base, args.api_key)
    
    if args.list_products:
        result = agent.get_available_products()
        print("Available Data Products:")
        print(result)
    elif args.get_contract:
        result = agent.get_product_contract(args.get_contract)
        print(f"Contract for {args.get_contract}:")
        print(result)
    elif args.ask:
        result = agent.process_query(args.ask)
        print("\nResponse:")
        print(result)
    else:
        print("Please provide a query with --ask, or use --list-products or --get-contract")


if __name__ == "__main__":
    main()
