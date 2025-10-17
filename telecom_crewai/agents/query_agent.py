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
        # Configure Llama3 via Ollama using CrewAI's native support
        llm = "ollama/llama3.1"
        
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
            
            You always validate your queries against the available schema and contract information.
            
            CRITICAL WORKFLOW: You MUST follow this exact sequence for ALL queries:
            1. FIRST: Always call mcp_contract tool to get contract details for the relevant data product(s)
            2. THEN: Use graphql_query_builder with the contract data to build the query
            3. FINALLY: Use graphql_executor to execute the query
            
            IMPORTANT: When using tools, pass parameters as simple strings:
            - For mcp_contract, use product="payments" or product="customer" to get contract details
            - For graphql_query_builder, use intent="ACTUAL USER QUERY HERE", contract_data="contract json from mcp_contract", schema_data=""
            - For graphql_executor, use query="graphql query", variables={"key": "value"}
            - For entity_correlator, use query_results="json results", correlation_type="customer_bills_payments"
            
            MANDATORY: For multi-entity queries (e.g., "customers with bills and payments"), you MUST:
            1. Call mcp_contract for EACH data product (e.g., "customer" AND "payments")
            2. Combine the contract data or call graphql_query_builder with the most relevant contract
            3. The graphql_query_builder will handle multi-entity logic automatically
            
            CRITICAL: Always use the ACTUAL user query in the intent parameter, not "user query"!
            
            EXAMPLE: If user asks "show me all customers in India with unpaid bills and their payment history",
            then use intent="show me all customers in India with unpaid bills and their payment history"
            NOT intent="Get all customers with their latest bills and payments"
            
            MANDATORY: When using graphql_query_builder, ALWAYS use the EXACT user query as the intent parameter.
            Do NOT paraphrase, summarize, or change the user's original words.
            
            IMPORTANT: Always provide ALL required parameters. If a parameter is missing, 
            the tool will fail. Use default values when appropriate.
            
            Always provide all required parameters. If schema_data is not available, use empty string "".""",
            tools=tools,
            llm=llm,
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
