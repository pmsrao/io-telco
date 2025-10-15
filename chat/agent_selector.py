"""
Agent Selector for Telecom Data Product Queries
Chooses between simple agent and CrewAI agent based on query complexity
"""

import re
import time
import sys
import os
from typing import Optional

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simple_agent import SimpleAgent
from crewai_agent import CrewAIAgent
from monitoring import get_metrics_collector


class AgentSelector:
    """Selects the appropriate agent based on query complexity"""
    
    def __init__(self, api_base: str = None, api_key: str = None):
        """
        Initialize the agent selector
        
        Args:
            api_base: Base URL for the GraphQL API
            api_key: API key for authentication
        """
        self.simple_agent = SimpleAgent(api_base, api_key)
        self.crewai_agent = CrewAIAgent(api_base, api_key)
        self.metrics_collector = get_metrics_collector()
    
    def select_agent(self, user_input: str) -> str:
        """
        Select the appropriate agent based on query complexity
        
        Args:
            user_input: The user's natural language request
        
        Returns:
            "simple" or "crewai"
        """
        # Simple heuristics to determine complexity
        if self._is_simple_query(user_input):
            return "simple"
        else:
            return "crewai"
    
    def _is_simple_query(self, user_input: str) -> bool:
        """
        Determine if a query is simple enough for the simple agent
        
        Args:
            user_input: The user's natural language request
        
        Returns:
            True if the query is simple, False otherwise
        """
        user_lower = user_input.lower()
        
        # Simple queries are typically:
        # 1. Single entity requests
        # 2. Direct lookups
        # 3. Basic filtering
        
        # Check for complex patterns that require CrewAI
        complex_patterns = [
            r'\b(and|or|with|including|also|additionally)\s+(?:me|all|the|a|an)\s+',  # Multiple conditions with context
            r'\b(compare|comparison|versus|vs)\b',  # Comparisons
            r'\b(aggregate|sum|total|count|average|max|min)\b',  # Aggregations
            r'\b(relationship|related|associated|linked)\b',  # Relationships
            r'\b(analyze|analysis|insight|pattern|trend)\b',  # Analysis
            r'\b(complex|detailed|comprehensive|complete)\b',  # Complex requests
        ]
        
        # Special case: "and" followed by "list" indicates multi-entity query
        # But exclude cases like "get bill X and list its payments" (single entity with action)
        if re.search(r'\band\s+list\b', user_lower):
            # Check if it's a single entity with action (e.g., "get bill X and list its payments")
            if re.search(r'\b(get|fetch|retrieve|show)\s+\w+\s+\w+.*\band\s+list\s+its?\s+\w+', user_lower):
                return True  # This is a simple query
            return False
        
        for pattern in complex_patterns:
            if re.search(pattern, user_lower):
                return False
        
        # Check for multiple entities (not filters)
        entities = []
        if any(word in user_lower for word in ['payment', 'payments']):
            entities.append('payments')
        if any(word in user_lower for word in ['bill', 'bills']):
            entities.append('bills')
        if any(word in user_lower for word in ['customer', 'customers']):
            entities.append('customers')
        if any(word in user_lower for word in ['subscription', 'subscriptions']):
            entities.append('subscriptions')
        
        # Only count as multiple entities if they're the main subject, not filters
        # e.g., "payments for account" = single entity (payments), "customers and payments" = multiple entities
        entity_indicators = ['show me', 'list', 'get', 'find', 'display']
        has_entity_indicator = any(indicator in user_lower for indicator in entity_indicators)
        
        if len(entities) > 1 and has_entity_indicator:
            return False
        
        # Check for complex time ranges or multiple filters
        time_indicators = ['last', 'between', 'from', 'to', 'since', 'until']
        time_count = sum(1 for indicator in time_indicators if indicator in user_lower)
        
        if time_count > 1:
            return False
        
        # Check for multiple status or filter conditions
        status_words = ['posted', 'failed', 'open', 'closed', 'active', 'inactive']
        status_count = sum(1 for status in status_words if status in user_lower)
        
        if status_count > 1:
            return False
        
        # If we get here, it's likely a simple query
        return True
    
    def process_query(self, user_input: str) -> str:
        """
        Process a user query using the appropriate agent
        
        Args:
            user_input: The user's natural language request
        
        Returns:
            A formatted response
        """
        # Start metrics collection
        query_id = self.metrics_collector.start_query(user_input, "selector")
        
        try:
            # Select agent and record selection timing
            agent_type = self.select_agent(user_input)
            self.metrics_collector.record_agent_selection(query_id, agent_type)
            
            print(f"🎯 Selected Agent: {agent_type.upper()}")
            print(f"📝 Query: {user_input}")
            print("=" * 60)
            
            # Record query execution start
            self.metrics_collector.record_query_execution_start(query_id)
            
            # Process query with selected agent
            if agent_type == "simple":
                result = self.simple_agent.process_query(user_input)
            else:
                result = self.crewai_agent.process_query(user_input)
            
            # Record successful completion
            self.metrics_collector.finish_query(
                query_id, 
                success=True, 
                result_size_bytes=len(str(result))
            )
            
            return result
            
        except Exception as e:
            # Record failed completion
            self.metrics_collector.finish_query(
                query_id, 
                success=False, 
                error_type=type(e).__name__, 
                error_message=str(e)
            )
            raise
    
    def get_available_products(self) -> str:
        """Get list of available data products using CrewAI agent"""
        return self.crewai_agent.get_available_products()
    
    def get_product_contract(self, product: str) -> str:
        """Get contract details for a specific product using CrewAI agent"""
        return self.crewai_agent.get_product_contract(product)


def main():
    """Main function for testing the agent selector"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Agent Selector for Telecom Data Products")
    parser.add_argument("--ask", type=str, help="Natural language query to process")
    parser.add_argument("--list-products", action="store_true", help="List available data products")
    parser.add_argument("--get-contract", type=str, help="Get contract for a specific product")
    parser.add_argument("--api-base", type=str, default="http://localhost:8000", help="API base URL")
    parser.add_argument("--api-key", type=str, default="dev-key", help="API key")
    
    args = parser.parse_args()
    
    # Initialize agent selector
    selector = AgentSelector(args.api_base, args.api_key)
    
    if args.list_products:
        result = selector.get_available_products()
        print("Available Data Products:")
        print(result)
    elif args.get_contract:
        result = selector.get_product_contract(args.get_contract)
        print(f"Contract for {args.get_contract}:")
        print(result)
    elif args.ask:
        result = selector.process_query(args.ask)
        print("\nResponse:")
        print(result)
    else:
        print("Please provide a query with --ask, or use --list-products or --get-contract")


if __name__ == "__main__":
    main()
