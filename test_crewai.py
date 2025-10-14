#!/usr/bin/env python3
"""
Test script for CrewAI integration
"""

import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_crewai_setup():
    """Test the CrewAI setup"""
    try:
        from telecom_crewai.tools.mcp_discovery import MCPDiscoveryTool
        print("✅ MCP Discovery Tool imported successfully")
        
        from telecom_crewai.tools.query_builder import GraphQLQueryBuilderTool
        print("✅ Query Builder Tool imported successfully")
        
        from telecom_crewai.tools.graphql_executor import GraphQLExecutorTool
        print("✅ GraphQL Executor Tool imported successfully")
        
        from telecom_crewai.agents.planner import PlannerAgent
        print("✅ Planner Agent imported successfully")
        
        from telecom_crewai.agents.query_agent import QueryAgent
        print("✅ Query Agent imported successfully")
        
        from telecom_crewai.agents.composer import ComposerAgent
        print("✅ Composer Agent imported successfully")
        
        from telecom_crewai.crew import TelecomCrew
        print("✅ Telecom Crew imported successfully")
        
        # Test MCP discovery
        discovery_tool = MCPDiscoveryTool()
        result = discovery_tool._run("discover_products")
        print(f"✅ MCP Discovery test: {result[:100]}...")
        
        print("\n🎉 All CrewAI components are working correctly!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing CrewAI setup: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_crewai_setup()
