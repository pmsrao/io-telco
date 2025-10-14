"""
Simple Agent wrapper for the existing MCP-based agent
"""

import asyncio
import os
import subprocess
import sys
from typing import Optional


class SimpleAgent:
    """Wrapper for the existing MCP-based agent"""
    
    def __init__(self, api_base: str = None, api_key: str = None):
        """
        Initialize the simple agent
        
        Args:
            api_base: Base URL for the GraphQL API (not used by simple agent)
            api_key: API key for authentication (not used by simple agent)
        """
        self.api_base = api_base
        self.api_key = api_key
    
    def process_query(self, user_input: str) -> str:
        """
        Process a user query using the existing MCP agent
        
        Args:
            user_input: The user's natural language request
        
        Returns:
            A formatted response
        """
        try:
            print(f"🤖 Simple Agent processing: {user_input}")
            print("=" * 60)
            
            # Set up environment variables for the MCP agent
            env = os.environ.copy()
            if self.api_base:
                env['TELECOM_API_BASE'] = self.api_base
            if self.api_key:
                env['TELECOM_API_KEY'] = self.api_key
            
            # Run the existing agent script
            result = subprocess.run([
                sys.executable, 
                os.path.join(os.path.dirname(__file__), 'agent.py'),
                '--server', 'mcp_server/server.py',
                '--ask', user_input
            ], 
            capture_output=True, 
            text=True, 
            env=env,
            cwd=os.path.dirname(os.path.dirname(__file__))
            )
            
            if result.returncode == 0:
                response = result.stdout.strip()
                print("=" * 60)
                print("✅ Simple Agent completed")
                return response
            else:
                error_msg = f"❌ Error in Simple Agent: {result.stderr}"
                print(error_msg)
                return error_msg
                
        except Exception as e:
            error_msg = f"❌ Error in Simple Agent: {str(e)}"
            print(error_msg)
            return error_msg
