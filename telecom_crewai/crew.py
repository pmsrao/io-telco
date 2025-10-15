"""
Main CrewAI Crew for Telecom Data Product Queries
Orchestrates the planner, query builder, executor, and composer agents
"""

import json
from crewai import Crew, Process, Task
from crewai.tools import BaseTool

from .agents.planner import PlannerAgent
from .agents.query_agent import QueryAgent
from .agents.composer import ComposerAgent
from .tools.mcp_discovery import MCPDiscoveryTool, MCPContractTool, MCPSchemaTool
from .tools.query_builder import GraphQLQueryBuilderTool
from .tools.graphql_executor import GraphQLExecutorTool
from .tools.entity_correlator import EntityCorrelatorTool


class TelecomCrew:
    """Main crew for handling telecom data product queries"""
    
    def __init__(self, api_base: str = "http://localhost:8000", api_key: str = "dev-key"):
        self.api_base = api_base
        self.api_key = api_key
        
        # Initialize tools
        self.mcp_discovery_tool = MCPDiscoveryTool(api_base)
        self.mcp_contract_tool = MCPContractTool(api_base)
        self.mcp_schema_tool = MCPSchemaTool(api_base)
        self.query_builder_tool = GraphQLQueryBuilderTool()
        self.graphql_executor_tool = GraphQLExecutorTool(api_base, api_key)
        self.entity_correlator_tool = EntityCorrelatorTool()
        
        # Initialize agents
        self.planner_agent = PlannerAgent([
            self.mcp_discovery_tool,
            self.mcp_contract_tool,
            self.mcp_schema_tool
        ])
        
        self.query_agent = QueryAgent([
            self.mcp_contract_tool,
            self.query_builder_tool,
            self.graphql_executor_tool,
            self.entity_correlator_tool
        ])
        
        self.composer_agent = ComposerAgent([])
        
        # Create the crew
        self.crew = self._create_crew()
    
    def _create_crew(self) -> Crew:
        """Create the CrewAI crew with tasks and agents"""
        
        # Task 1: Plan the query
        plan_task = Task(
            description="""
            Analyze the user's request and create a plan for query execution.
            Use the MCP discovery tools to understand what data products are available.
            Determine which data products and operations are needed to fulfill the request.
            """,
            agent=self.planner_agent.agent,
            expected_output="A clear plan for executing the query, including which data products and operations to use"
        )
        
        # Task 1: Build and execute GraphQL query (simplified)
        query_task = Task(
            description="""
            Build a valid GraphQL query based on the user's intent and execute it.
            Use the graphql_query_builder tool to create the query, then use graphql_executor to run it.
            Return the final results.
            """,
            agent=self.query_agent.agent,
            expected_output="GraphQL query results with data",
            context=[]
        )
        
        # Task 3: Execute the query
        execute_task = Task(
            description="""
            Execute the GraphQL query against the telecom API.
            Handle any errors and return the results.
            """,
            agent=self.query_agent.agent,  # Use the query agent for execution
            expected_output="Query execution results",
            context=[query_task]
        )
        
        # Task 4: Correlate entities (if multi-entity query)
        correlate_task = Task(
            description="""
            If the query involves multiple entities (customers, bills, payments),
            correlate the data to provide comprehensive results.
            """,
            agent=self.query_agent.agent,
            expected_output="Correlated data across entities",
            context=[execute_task]
        )
        
        # Task 5: Compose the response
        compose_task = Task(
            description="""
            Format the query results into a clear, user-friendly response.
            Answer the user's original question directly and provide context.
            """,
            agent=self.composer_agent.agent,
            expected_output="A formatted, user-friendly response that answers the user's question",
            context=[execute_task]
        )
        
        return Crew(
            agents=[self.query_agent.agent],  # Only query agent for maximum speed
            tasks=[query_task],  # Single task - just build and execute query
            process=Process.sequential,
            verbose=True,
            max_iter=2,   # Reduced iterations to prevent loops
            max_rpm=200   # Lower rate limit for stability
        )
    
    def process_query(self, user_intent: str) -> str:
        """
        Process a user query through the entire crew
        
        Args:
            user_intent: The user's natural language request
        
        Returns:
            A formatted response to the user's query
        """
        try:
            # Set the user intent for all tasks
            inputs = {"user_intent": user_intent}
            
            # Execute the crew
            result = self.crew.kickoff(inputs=inputs)
            
            return str(result)
            
        except Exception as e:
            return f"Error processing query: {str(e)}"
    
    def get_available_products(self) -> str:
        """Get list of available data products"""
        try:
            return self.mcp_discovery_tool._run("discover_products")
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    def get_product_contract(self, product: str) -> str:
        """Get contract details for a specific product"""
        try:
            return self.mcp_contract_tool._run(product)
        except Exception as e:
            return json.dumps({"error": str(e)})
