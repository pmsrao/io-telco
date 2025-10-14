#!/usr/bin/env python3
"""
Simple test for CrewAI integration
"""

import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_simple_crewai():
    """Test a simple CrewAI query"""
    try:
        from telecom_crewai.tools.mcp_discovery import MCPDiscoveryTool
        from telecom_crewai.tools.query_builder import GraphQLQueryBuilderTool
        from telecom_crewai.tools.graphql_executor import GraphQLExecutorTool
        
        print("🔍 Testing MCP Discovery...")
        discovery_tool = MCPDiscoveryTool()
        products_result = discovery_tool._run("discover_products")
        print(f"✅ Available products: {products_result}")
        
        print("\n🔍 Testing Contract Discovery...")
        from telecom_crewai.tools.mcp_discovery import MCPContractTool
        contract_tool = MCPContractTool()
        contract_result = contract_tool._run("payments")
        print(f"✅ Payments contract: {contract_result[:200]}...")
        
        print("\n🔍 Testing Query Builder...")
        query_builder = GraphQLQueryBuilderTool()
        query_result = query_builder._run(
            intent="show POSTED payments for ACC-1002",
            contract_data=contract_result
        )
        print(f"✅ Generated query: {query_result}")
        
        print("\n🔍 Testing GraphQL Executor...")
        executor = GraphQLExecutorTool()
        # Parse the query result to get the actual query
        import json
        query_data = json.loads(query_result)
        exec_result = executor._run(
            query=query_data.get("query", ""),
            variables=query_data.get("variables", {})
        )
        print(f"✅ Execution result: {exec_result}")
        
        print("\n🎉 Simple CrewAI test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error in simple CrewAI test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_simple_crewai()
