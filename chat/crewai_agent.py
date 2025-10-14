"""
CrewAI Agent for Telecom Data Product Queries
Provides a high-level interface for complex natural language queries
"""

import os
import sys
from typing import Optional

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telecom_crewai.crew import TelecomCrew


class CrewAIAgent:
    """CrewAI-based agent for complex telecom data product queries"""
    
    def __init__(self, api_base: str = None, api_key: str = None):
        """
        Initialize the CrewAI agent
        
        Args:
            api_base: Base URL for the GraphQL API (defaults to env var)
            api_key: API key for authentication (defaults to env var)
        """
        self.api_base = api_base or os.getenv("TELECOM_API_BASE", "http://localhost:8000")
        self.api_key = api_key or os.getenv("TELECOM_API_KEY", "dev-key")
        
        # Initialize the crew
        self.crew = TelecomCrew(self.api_base, self.api_key)
    
    def process_query(self, user_input: str) -> str:
        """
        Process a user query using the CrewAI crew
        
        Args:
            user_input: The user's natural language request
        
        Returns:
            A formatted response
        """
        try:
            print(f"🤖 CrewAI Agent processing: {user_input}")
            print("=" * 60)
            
            # Process through the crew
            result = self.crew.process_query(user_input)
            
            print("=" * 60)
            print("✅ CrewAI Agent completed")
            
            return result
            
        except Exception as e:
            error_msg = f"❌ Error in CrewAI Agent: {str(e)}"
            print(error_msg)
            return error_msg
    
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
