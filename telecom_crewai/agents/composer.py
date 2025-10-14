"""
Composer Agent for CrewAI
Formats and presents query results in a user-friendly way
"""

from crewai import Agent
from crewai.tools import BaseTool
from typing import List


class ComposerAgent:
    """Agent that formats and presents query results"""
    
    def __init__(self, tools: List[BaseTool]):
        self.agent = Agent(
            role="Response Composer",
            goal="Format and present query results in a clear, user-friendly way",
            backstory="""You are an expert at presenting data in a clear, understandable format.
            You take raw query results and transform them into meaningful, well-formatted responses
            that answer the user's original question.
            
            You excel at:
            - Summarizing data in business terms
            - Highlighting key insights and patterns
            - Formatting results for readability
            - Providing context and explanations
            - Suggesting follow-up questions when appropriate
            
            You always ensure the response directly addresses what the user asked for.""",
            tools=tools,
            verbose=True,
            allow_delegation=False
        )
    
    def compose_response(self, user_intent: str, query_result: str, original_query: str = None) -> str:
        """
        Format query results into a user-friendly response
        
        Args:
            user_intent: The user's original request
            query_result: JSON string with the query results
            original_query: The GraphQL query that was executed
        
        Returns:
            A formatted, user-friendly response
        """
        task = f"""
        Format these query results into a clear, user-friendly response:
        
        User's Original Request: "{user_intent}"
        Query Results: {query_result}
        GraphQL Query Used: {original_query or "Not provided"}
        
        Please:
        1. Analyze the query results to understand what data was returned
        2. Format the results in a clear, readable way
        3. Answer the user's original question directly
        4. Highlight any important insights or patterns in the data
        5. Provide context and explanations where helpful
        6. Suggest follow-up questions if appropriate
        
        Make sure your response is professional, clear, and directly addresses what the user asked for.
        """
        
        result = self.agent.execute_task(task)
        return result
