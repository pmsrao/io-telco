"""
Query Agent for CrewAI
Builds GraphQL queries from user intent and contract information
"""

from crewai import Agent
from crewai.tools import BaseTool
from typing import List


class QueryAgent:
    """Agent that builds GraphQL queries from user intent and contract data"""
    
    def __init__(self, tools: List[BaseTool]):
        self.agent = Agent(
            role="GraphQL Query Builder",
            goal="Build valid GraphQL queries from user intent and contract information",
            backstory="""You are an expert GraphQL query builder who specializes in telecom data products.
            You take user intent and contract information to build precise, valid GraphQL queries.
            
            You understand:
            - GraphQL syntax and best practices
            - Telecom business domain (payments, customers, bills, etc.)
            - How to map natural language to GraphQL operations
            - How to use contract information to build valid queries
            
            You always validate your queries against the available schema and contract information.""",
            tools=tools,
            verbose=True,
            allow_delegation=False
        )
    
    def build_query(self, user_intent: str, contract_data: str, plan: str = None) -> str:
        """
        Build a GraphQL query from user intent and contract data
        
        Args:
            user_intent: The user's natural language request
            contract_data: JSON string with contract information
            plan: Optional plan from the planner agent
        
        Returns:
            A GraphQL query ready for execution
        """
        task = f"""
        Build a GraphQL query based on this information:
        
        User Intent: "{user_intent}"
        Contract Data: {contract_data}
        Plan: {plan or "No specific plan provided"}
        
        Please:
        1. Analyze the user intent to understand what data they need
        2. Use the contract data to understand available operations and filters
        3. Build a valid GraphQL query that will return the requested data
        4. Include appropriate filters and variables
        5. Ensure the query follows GraphQL best practices
        
        Return the query in a format that can be executed by the GraphQL executor.
        """
        
        result = self.agent.execute_task(task)
        return result
