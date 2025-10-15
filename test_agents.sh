#!/bin/bash

# Set up environment variables for testing
export TELECOM_API_BASE="http://localhost:8000"
export TELECOM_API_KEY="dev-key"

echo "🧪 Testing Telecom Agents with GraphQL Server"
echo "=============================================="
echo "API Base: $TELECOM_API_BASE"
echo ""

# Test 1: Simple Agent
echo "📋 Test 1: Simple Agent - Basic Payment Query"
echo "----------------------------------------------"
python chat/agent.py --server mcp_server/server.py --ask "show me payments for account ACC-1002"
echo ""

# Test 2: Agent Selector - Simple Query
echo "📋 Test 2: Agent Selector - Simple Query"
echo "----------------------------------------"
python chat/agent_selector.py --ask "show me payments for account ACC-1002"
echo ""

# Test 3: Agent Selector - Complex Query
echo "📋 Test 3: Agent Selector - Complex Query"
echo "-----------------------------------------"
python chat/agent_selector.py --ask "show me all customers in India with unpaid bills and their payment history"
echo ""

echo "✅ Testing Complete!"
