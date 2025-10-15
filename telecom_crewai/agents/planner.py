"""
Planner Agent for CrewAI
Analyzes user intent and determines which data products and operations to use
"""

from crewai import Agent
from crewai.tools import BaseTool
from typing import List


class PlannerAgent:
    """Agent that analyzes user intent and plans the query execution"""
    
    def __init__(self, tools: List[BaseTool]):
        # Configure Llama3 via Ollama using CrewAI's native support
        llm = "ollama/llama3.1"
        
        self.agent = Agent(
            role="Data Product Planner",
            goal="Analyze user intent and determine which data products and operations are needed to fulfill the request",
            backstory="""You are an expert data product planner who understands telecom business domains.
            You analyze user requests and determine which data products (payments, customer, etc.) and 
            specific operations (list_payments, get_customer, etc.) are needed to answer the user's question.
            
            You have access to the MCP discovery tools to understand what data products and operations are available.
            Always start by discovering available data products before making recommendations.
            
            IMPORTANT: When using tools, always pass parameters as simple strings or key-value pairs. 
            For mcp_discovery, use action="discover_products" to get available data products.
            For mcp_contract, use product="payments" (or other product name) to get contract details.
            For mcp_schema, call without parameters to get the GraphQL schema.
            
            CRITICAL: Always pass the EXACT user query to the query builder, not generic text!
            
            For complex queries involving multiple entities (customers, bills, payments), 
            recommend using the multi_entity_query tool which handles correlation automatically.""",
            tools=tools,
            llm=llm,
            verbose=True,
            allow_delegation=False
        )
    
    def plan_query(self, user_intent: str) -> str:
        """
        Analyze user intent and create a plan for query execution
        
        Args:
            user_intent: The user's natural language request
        
        Returns:
            A plan for executing the query
        """
        task = f"""
        Analyze this user request and create a plan for query execution:
        
        User Request: "{user_intent}"
        
        Please:
        1. First, discover what data products are available using the MCP discovery tools
        2. Analyze the user intent to understand what data they need
        3. Determine which data products and operations are most appropriate
        4. Create a clear plan for executing the query
        
        Provide your analysis and plan in a structured format.
        """
        
        result = self.agent.execute_task(task)
        return result
