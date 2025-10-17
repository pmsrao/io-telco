# 📘 Demo Flow — GraphQL Data Product Runtime

This markdown captures the **end-to-end demo flow** for the Telecom Data Product runtime — from spec to live API, complete with narrative points that can be spoken during a demo session.

## 🎯 Demo Paths Available

This system supports **five distinct demo paths**:

1. **🚀 Production MCP Demo** (`make demo-prod`) - Uses the real MCP server for AI agent communication (stdio)
2. **🌐 HTTP MCP Demo** (`make demo-http`) - Uses standalone HTTP MCP server with real-time logging (2 queries)
3. **🌐 HTTP MCP Full Demo** (`make demo-http-full`) - Uses HTTP MCP server with 3 queries (recommended for production)
4. **🧪 Mock MCP Demo** (`make demo-mock`) - Uses mock registry for contract registration + production MCP for agent communication
5. **🤖 Enhanced Agent Demo** - Uses the new CrewAI + Agent Selector for intelligent query processing

All paths demonstrate the same core functionality but with different levels of AI agent sophistication and communication methods.

---

## 🚀 Quick Start Demo Flow

### **Complete Demo in 5 Steps**

1. **Setup Environment**
   ```bash
   # Install dependencies
   pip install -r requirements.txt
   pip install crewai crewai-tools
   
   # Create .env file with your Databricks credentials
   # (See detailed setup below)
   ```

2. **Generate & Start System**
   ```bash
   # Generate registry and start GraphQL API
   make regen
   make run-graphql &
   sleep 3
   
   # Verify system is running
   make health
   ```

3. **Test Basic Functionality**
   ```bash
   # Test direct GraphQL API
   curl -s -H "x-api-key: dev-key" -H "Content-Type: application/json" \
        -d '{"query":"{ list_payments(limit: 3) { payment_id amount status } }"}' \
        "http://localhost:8000/graphql" | jq .
   ```

4. **Test Enhanced Agent System**
   ```bash
   # Test simple query (uses Simple Agent)
   python chat/agent_selector.py --ask "show payments for ACC-1002"
   
   # Test complex query (uses CrewAI Agent)
   python chat/agent_selector.py --ask "show me all customers in India with unpaid bills and their payment history"
   ```

5. **Test Contract Discovery**
   ```bash
   # Test well-known endpoints
   curl -s http://localhost:8000/.well-known/telecom.registry.index | jq .
   curl -s http://localhost:8000/.well-known/telecom.registry/payments.yaml | jq .
   ```

**🎉 You've now demonstrated the complete system: metadata-driven API generation, contract discovery, and intelligent AI agent orchestration!**

---

## ⚙️ Setup & Prerequisites

Before running the demo, ensure the following setup is complete:

### 🧾 1️⃣ Environment configuration
Create a `.env` file in your project root with these variables:
```bash
DATABRICKS_SERVER_HOSTNAME=<your-databricks-host>
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/<warehouse-id>
DATABRICKS_TOKEN=dapi<your-token>
CATALOG=india_dataengineer_recruitment
SCHEMA=telco_silver
API_KEY=dev-key
TENANT=telecom
STAGE=dev
```

### 🧩 2️⃣ Python environment
Install dependencies:
```bash
pip install -r requirements.txt
```
If missing `fastapi` or `ariadne` during later steps, install them directly:
```bash
pip install fastapi ariadne uvicorn python-dotenv databricks-sql-connector
```

**For Enhanced Agent Demo (CrewAI):**
```bash
pip install crewai crewai-tools
```

### 🧰 3️⃣ Databricks connectivity test
Confirm your `.env` variables work:
```bash
python - <<'PY'
from databricks import sql
import os
conn = sql.connect(
    server_hostname=os.environ['DATABRICKS_SERVER_HOSTNAME'],
    http_path=os.environ['DATABRICKS_HTTP_PATH'],
    access_token=os.environ['DATABRICKS_TOKEN']
)
cur = conn.cursor()
cur.execute('SELECT current_user(), current_catalog(), current_schema()')
print(cur.fetchall())
cur.close(); conn.close()
PY
```
✅ Expect your Databricks username and schema details printed.

### 🧱 4️⃣ MCP Server Setup

**For Production MCP Demo (Stdio):**
- No additional setup needed - the production MCP server (`mcp_server/server.py`) will be used automatically
- This server communicates with AI agents via stdio protocol
- **Note**: Logs are not visible in the main console (they go to subprocess stdout)

**For HTTP MCP Demo:**
- Start the HTTP MCP server separately: `make run-mcp-http-server`
- This server runs on port 8001 and provides real-time logging
- **Benefit**: You can see all tool invocations and responses in real-time
- **Use case**: Development, debugging, and better visibility into agent interactions

**For Mock MCP Demo:**
- The mock MCP registry will be started automatically during the demo
- This simulates a real MCP registry for contract registration

Now you're ready for the full demo run.

---

## 🎯 Goal
Show how a single product spec (e.g., `dp/telecom.yml`) can automatically generate:
- a runtime registry →
- GraphQL API →
- OpenAPI & SDL contracts →
- and register them with an MCP/Agent registry for discovery.

No manual coding per product.

---

## 🧠 High-Level Narrative
> “Our Data Product APIs are generated and deployed fully from metadata — no boilerplate code. The system reads a YAML spec, builds GraphQL schema and resolvers dynamically, connects to Databricks SQL, and exports contracts that can be registered with any agent or MCP for discovery.”

---

## 🧩 Step-by-Step Demo Flow

### 1️⃣ Generate registry and schema
```bash
make regen
```
**Purpose:** Converts `dp/telecom.yml` → runtime metadata (`registry/*.yaml`) and validates stitched SDL (GraphQL schema).

**Talking point:** "From the product spec, we automatically infer entities, relationships, and filters — these are persisted as registry metadata used at runtime."

---

### 2️⃣ Start GraphQL runtime
```bash
make run-graphql
```
**Purpose:** Starts metadata-driven runtime that builds schema and resolvers dynamically.

**Check health:**
```bash
make health
```
✅ Expected: `{ "ok": true, "mode": "dynamic" }`

**Talking point:** "The runtime loads the registry, constructs GraphQL schema, wires resolvers to Databricks SQL, and verifies connectivity."

---

### 3️⃣ Export contracts (OpenAPI + SDL)
```bash
make export
```
**Purpose:** Emits per-product contracts to `contracts/`, e.g. `contracts/customer.graphql`, `contracts/payments.openapi.yaml`.

**Talking point:** "These are self-describing contracts — standard GraphQL SDL and OpenAPI definitions — which external systems or agents can introspect or generate clients from."

---

### 4️⃣ Choose Your Demo Path

#### 🚀 **Path A: Production MCP Demo** (Basic - Stdio)
```bash
make demo-prod
```
**What happens:**
- Uses the production MCP server (`mcp_server/server.py`) for AI agent communication
- Demonstrates real MCP protocol communication via stdio
- Shows natural language → GraphQL query translation
- **No contract registration needed** - direct agent communication
- **Note**: MCP server logs are not visible (they go to subprocess stdout)

**Talking point:** "This demonstrates the production MCP server in action - AI agents can directly communicate with our GraphQL API using the MCP protocol via stdio communication."

#### 🌐 **Path B: HTTP MCP Demo** (Development/Debugging)
```bash
# Start HTTP MCP server in one terminal
make run-mcp-http-server

# Run demo in another terminal
make demo-http
```
**What happens:**
- Uses standalone HTTP MCP server on port 8001
- **Real-time logging visible** - you can see all tool invocations
- Demonstrates HTTP-based MCP communication
- Shows natural language → GraphQL query translation
- **Better for debugging** - full visibility into agent interactions

**Talking point:** "This demonstrates the HTTP MCP server which provides real-time logging and better visibility into how AI agents interact with our GraphQL API. Perfect for development and debugging."

#### 🌐 **Path C: HTTP MCP Full Demo** (Production Recommended)
```bash
# Start HTTP MCP server in one terminal
make run-mcp-http-server

# Run full demo in another terminal
make demo-http-full
```
**What happens:**
- Uses standalone HTTP MCP server on port 8001
- **Real-time logging visible** - you can see all tool invocations
- Runs **3 comprehensive queries** (same as demo-prod)
- Demonstrates HTTP-based MCP communication
- **Best for production** - full visibility + comprehensive testing

**Talking point:** "This is our recommended production demo - it combines the comprehensive 3-query testing of demo-prod with the real-time logging and HTTP-based communication of the HTTP MCP server. Perfect for production environments where you need both thorough testing and full observability."

#### 🧪 **Path D: Mock MCP Demo** (Development/Testing)
```bash
make demo-mock
```
**What happens:**
- Starts mock MCP registry on port 9000
- Registers contracts with the mock registry
- Uses production MCP server for agent communication
- Shows complete contract registration workflow

**Talking point:** "This shows the complete workflow including contract registration with an MCP registry, followed by agent communication."

#### 🤖 **Path E: Enhanced Agent Demo** (Advanced - NEW!)
```bash
# Test the new CrewAI + Agent Selector system
python chat/agent_selector.py --ask "show POSTED payments for ACC-1002"
```
**What happens:**
- **Intelligent Agent Selection**: Automatically chooses between simple and CrewAI agents based on query complexity
- **Simple Queries**: Uses existing MCP agent for straightforward requests
- **Complex Queries**: Uses CrewAI with contract discovery for multi-step operations
- **Contract-Driven**: All operations discovered from MCP registry metadata

**Talking point:** "This demonstrates our enhanced AI agent system that intelligently selects the appropriate agent based on query complexity, with CrewAI handling complex multi-step operations using contract discovery."

**Additional Enhanced Agent Tests:**
```bash
# Test simple query (uses simple agent)
python chat/agent_selector.py --ask "show payments for ACC-1002"

# Test complex query (uses CrewAI agent)
python chat/agent_selector.py --ask "show me all customers in India with unpaid bills and their payment history"

# Test MCP discovery tools directly
python test_crewai.py

# Test CrewAI components individually
python test_simple_crewai.py
```

---

### 5️⃣ Direct GraphQL API Testing
```bash
python - <<'PY'
import requests, json
q = """
query {
  list_customers(limit: 5) { customer_id full_name status }
  list_bills(limit: 5) { bill_id amount_due status }
}
"""
r = requests.post("http://127.0.0.1:8000/graphql", 
                  headers={"x-api-key": "dev-key"}, 
                  json={"query": q})
print(json.dumps(r.json(), indent=2))
PY
```
✅ Expected output:
```json
{
  "data": {
    "list_customers": [
      {"customer_id": "CUST001", "full_name": "John Doe", "status": "Active"}
    ],
    "list_bills": [
      {"bill_id": "B001", "amount_due": 120.5, "status": "Unpaid"}
    ]
  }
}
```

**Talking point:** "This query runs live against Databricks SQL — no hand-written resolvers, all metadata-driven."

---

### 6️⃣ Bonus — Modify spec and regenerate

**Change something in** `dp/telecom.yml` (e.g., add a filter or alias) → then rerun:
```bash
make all
```

**Talking point:** "We can evolve the product definition declaratively. The contracts, schema, and registry all stay consistent automatically."

---

## 🔧 MCP Communication Methods

The system supports different ways to communicate with MCP servers, each with its own benefits:

### 📡 **Stdio MCP (Default)**
- **How it works**: MCP server runs as subprocess, communication via stdin/stdout
- **Pros**: Simple, no network setup required
- **Cons**: Logs not visible, harder to debug
- **Use case**: Simple applications and production

### 🌐 **HTTP MCP (Recommended for Development)**
- **How it works**: MCP server runs as standalone HTTP server on port 8001
- **Pros**: Real-time logging, easy debugging, multiple clients
- **Cons**: Requires network setup
- **Use case**: Development, debugging, production

### 🧪 **Testing MCP Methods**
```bash
# Test and compare different MCP communication methods
make test-mcp-methods

# Start simple HTTP MCP server for testing
python simple_http_mcp.py

# Test HTTP MCP communication
python demo_mcp_difference.py
```

### 📊 **MCP Method Comparison**

| Method | Logging | Debugging | Scalability | Use Case |
|--------|---------|-----------|-------------|----------|
| Stdio | ❌ Hidden | ❌ Hard | ❌ Limited | Production |
| HTTP | ✅ Visible | ✅ Easy | ✅ Multiple clients | Development |

---

## 🧩 Services Running During Demo

### 🚀 Production MCP Demo (Stdio)
| Component | Purpose | Port/Protocol |
|------------|----------|---------------|
| GraphQL Runtime | Metadata-driven API layer | `8000` |
| Databricks SQL Warehouse | Actual data backend | remote |
| Production MCP Server | AI agent communication | stdio protocol |
| CLI Agent | Natural language → GraphQL | local process |

### 🌐 HTTP MCP Demo
| Component | Purpose | Port/Protocol |
|------------|----------|---------------|
| GraphQL Runtime | Metadata-driven API layer | `8000` |
| Databricks SQL Warehouse | Actual data backend | remote |
| HTTP MCP Server | AI agent communication | `8001` (HTTP) |
| HTTP Agent | Natural language → GraphQL | local process |

### 🧪 Mock MCP Demo
| Component | Purpose | Port/Protocol |
|------------|----------|---------------|
| GraphQL Runtime | Metadata-driven API layer | `8000` |
| Databricks SQL Warehouse | Actual data backend | remote |
| Mock MCP Registry | Contract registration | `9000` |
| Production MCP Server | AI agent communication | stdio protocol |
| CLI Agent | Natural language → GraphQL | local process |

### 🤖 Enhanced Agent Demo
| Component | Purpose | Port/Protocol |
|------------|----------|---------------|
| GraphQL Runtime | Metadata-driven API layer | `8000` |
| Databricks SQL Warehouse | Actual data backend | remote |
| Well-Known Endpoints | Contract discovery | `8000` |
| Agent Selector | Intelligent agent routing | local process |
| Simple Agent | Basic MCP communication | local process |
| CrewAI Agent | Complex query orchestration | local process |
| MCP Discovery Tools | Contract introspection | local process |

---

## 🤖 Production MCP Server Details

### What is the Production MCP Server?

The **Production MCP Server** (`mcp_server/server.py`) is the **real Model Context Protocol server** that enables AI agents to communicate with your GraphQL API. It's not a mock or development tool - it's the actual production component.

### Key Features

#### 🔧 **Tool: `telecom.graphql.run`**
- **Purpose**: Allows AI agents to execute GraphQL queries against your API
- **Parameters**: 
  - `query`: GraphQL query string
  - `variables`: Optional query variables
- **Returns**: JSON response from your GraphQL API
- **Authentication**: Automatically injects API key from environment

#### 📚 **Resources: Schema & Registry Discovery**
- **`resource://telecom/graphql-sdl`**: Provides GraphQL Schema Definition Language
- **`resource://telecom/registry-index`**: Registry metadata for agent discovery
- **`resource://telecom/registry/customer.yaml`**: Customer data product specification
- **`resource://telecom/registry/payments.yaml`**: Payments data product specification

#### 🔍 **Enhanced Discovery Tools** (NEW!)
- **`telecom.discover.products`**: Discover available data products and contracts
- **`telecom.get.contract`**: Get contract details for specific data products
- **`telecom.schema.introspect`**: Get complete GraphQL schema for all products

#### 🔒 **Security & Observability**
- **API Key Injection**: Automatically adds `x-api-key` header to requests
- **Correlation IDs**: Tracks requests with unique identifiers
- **Structured Logging**: JSON-formatted logs for monitoring
- **Error Handling**: Graceful error responses with context

### How It Works

1. **Agent Communication**: Uses MCP stdio protocol (stdin/stdout)
2. **Request Forwarding**: Forwards GraphQL queries to your API at `TELECOM_API_BASE`
3. **Response Processing**: Returns structured JSON responses to agents
4. **Resource Serving**: Provides schema and registry information for agent discovery

### Environment Variables

```bash
# Required for MCP server operation
TELECOM_API_BASE=http://localhost:8000    # Your GraphQL API base URL
TELECOM_GQL_PATH=/graphql                 # GraphQL endpoint path
TELECOM_API_KEY=dev-key                   # API key for authentication
```

### Usage Examples

#### Direct MCP Tool Call
```bash
# One-off MCP call
make mcp-call
```

#### Agent Integration
```bash
# Natural language queries via agent
make demo-prod
```

#### Custom Agent Script
```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async with stdio_client(StdioServerParameters(
    command="python",
    args=["mcp_server/server.py"]
)) as (reader, writer):
    async with ClientSession(reader, writer) as session:
        await session.initialize()
        
        result = await session.call_tool("telecom.graphql.run", {
            "query": "query { list_payments(limit: 5) { payment_id amount status } }",
            "variables": {}
        })
        
        print(result.content[0].text)
```

### Production Deployment

For production deployment:

1. **Environment Setup**: Configure production environment variables
2. **Process Management**: Use systemd, Docker, or process manager
3. **Monitoring**: Monitor stdio communication and error logs
4. **Scaling**: Run multiple instances behind load balancer if needed

---

## 🌐 HTTP MCP Server Details (NEW!)

### What is the HTTP MCP Server?

The **HTTP MCP Server** (`mcp_server/http_server.py`) is a standalone HTTP server that provides the same MCP functionality as the stdio version but with **real-time logging and better debugging capabilities**.

### Key Features

#### 🔧 **HTTP API Endpoints**
- **`GET /`** - Health check endpoint
- **`GET /tools`** - List available tools
- **`POST /tools/execute`** - Execute tools with arguments

#### 📊 **Real-Time Logging**
- **Tool Invocations**: See exactly when tools are called
- **Request/Response**: Full visibility into HTTP requests
- **Performance Metrics**: Duration and response size tracking
- **Error Handling**: Clear error messages and stack traces

#### 🔍 **Available Tools**
- **`telecom.discover.products`** - Discover available data products
- **`telecom.contract.get`** - Get contract details for specific products
- **`telecom.schema.get`** - Get GraphQL schema
- **`telecom.graphql.run`** - Execute GraphQL queries

### How to Use

#### 1. **Start HTTP MCP Server**
```bash
# Start the server
make run-mcp-http-server

# Server will be available at http://localhost:8001
# Logs will be visible in real-time
```

#### 2. **Test HTTP Endpoints**
```bash
# Health check
curl http://localhost:8001/

# List tools
curl http://localhost:8001/tools

# Execute a tool
curl -X POST http://localhost:8001/tools/execute \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "telecom.discover.products", "arguments": {}}'
```

#### 3. **Use HTTP Agent**
```bash
# Set environment variable
export MCP_HTTP_BASE=http://localhost:8001

# Run HTTP agent
python chat/http_agent.py --ask "show payments for ACC-1002"
```

### Benefits Over Stdio MCP

| Feature | Stdio MCP | HTTP MCP |
|---------|-----------|----------|
| **Logging** | ❌ Hidden | ✅ **Real-time visible** |
| **Debugging** | ❌ Hard | ✅ **Easy with curl/Postman** |
| **Monitoring** | ❌ Limited | ✅ **Full HTTP monitoring** |
| **Multiple Clients** | ❌ One per process | ✅ **Multiple simultaneous** |
| **Scalability** | ❌ Limited | ✅ **Better for production** |

### Environment Variables

```bash
# Required for HTTP MCP server
TELECOM_API_BASE=http://localhost:8000    # Your GraphQL API base URL
TELECOM_GQL_PATH=/graphql                 # GraphQL endpoint path
TELECOM_API_KEY=dev-key                   # API key for authentication
```

### Production Deployment

For production deployment:

1. **Process Management**: Use systemd, Docker, or process manager
2. **Load Balancing**: Run multiple instances behind load balancer
3. **Monitoring**: Use standard HTTP monitoring tools
4. **Security**: Add authentication and rate limiting

---

## 🤖 Enhanced Agent System Details (NEW!)

### What is the Enhanced Agent System?

The **Enhanced Agent System** is a sophisticated AI agent architecture that combines the existing MCP-based agent with advanced CrewAI orchestration for complex queries. It provides intelligent agent selection and contract-driven query processing.

### Key Components

#### 🎯 **Agent Selector**
- **Purpose**: Intelligently chooses between simple and CrewAI agents based on query complexity
- **Location**: `chat/agent_selector.py`
- **Logic**: Analyzes natural language queries to determine complexity and routing

#### 🤖 **Simple Agent**
- **Purpose**: Wrapper for existing MCP-based agent for straightforward queries
- **Location**: `chat/simple_agent.py`
- **Use Case**: Single-entity queries, direct lookups, basic filtering

#### 🧠 **CrewAI Agent**
- **Purpose**: Advanced multi-agent orchestration for complex queries
- **Location**: `chat/crewai_agent.py`
- **Use Case**: Multi-entity queries, complex relationships, multi-step operations

#### 🔧 **CrewAI Tools**
- **MCP Discovery Tool**: Discovers available data products and contracts
- **Query Builder Tool**: Builds GraphQL queries from natural language and contracts
- **GraphQL Executor Tool**: Executes queries against the API

#### 👥 **CrewAI Agents**
- **Planner Agent**: Analyzes user intent and determines required data products
- **Query Agent**: Builds valid GraphQL queries from contracts
- **Composer Agent**: Formats results in user-friendly responses

### How Agent Selection Works

#### Simple Query Examples (→ Simple Agent)
```bash
# Single entity, basic filtering
"show payments for ACC-1002"
"get bill BILL-9001"
"list customers with status active"
```

#### Complex Query Examples (→ CrewAI Agent)
```bash
# Multiple entities, relationships, analysis
"show me all customers in India with unpaid bills and their payment history"
"compare payment patterns between different customer segments"
"analyze billing trends for the last quarter"
```

### Testing the Enhanced System

#### 1. **Test Agent Selection**
```bash
# Simple query (should use Simple Agent)
python chat/agent_selector.py --ask "show payments for ACC-1002"

# Complex query (should use CrewAI Agent)
python chat/agent_selector.py --ask "show me all customers in India with unpaid bills and their payment history"
```

#### 2. **Test Individual Components**
```bash
# Test CrewAI setup
python test_crewai.py

# Test CrewAI tools directly
python test_simple_crewai.py

# Test MCP discovery
python chat/crewai_agent.py --list-products
python chat/crewai_agent.py --get-contract payments
```

#### 3. **Test Well-Known Endpoints**
```bash
# Test contract discovery endpoints
curl -s http://localhost:8000/.well-known/telecom.registry.index | jq .
curl -s http://localhost:8000/.well-known/telecom.registry/payments.yaml | jq .
curl -s http://localhost:8000/.well-known/telecom.graphql.sdl | head -20
```

### Expected Behavior

#### Simple Agent Response
```
🎯 Selected Agent: SIMPLE
📝 Query: show payments for ACC-1002
============================================================
🤖 Simple Agent processing: show payments for ACC-1002
============================================================
SANITIZED QUERY => query($acct:String!,$from:String!,$to:String!){   
  list_payments(filters:{ account_id:$acct, status:"POSTED", from_time:$from, to_time:$to }, limit:50){     
    payment_id amount currency status created_at   
  } 
}
Executing tool with window: 2025-09-13T00:00:00Z → 2025-10-13T17:18:06Z
{
  "data": {
    "list_payments": [...]
  }
}
```

#### CrewAI Agent Response
```
🎯 Selected Agent: CREWAI
📝 Query: show me all customers in India with unpaid bills and their payment history
============================================================
🤖 CrewAI Agent processing: show me all customers in India with unpaid bills and their payment history
============================================================
╭─────────────────────────── Crew Execution Started ───────────────────────────╮
│ Crew Execution Started                                                      │
│ Name: crew                                                                  │
│ ID: 4e277a11-1437-44eb-a886-2c044aafe4db                                    │
╰──────────────────────────────────────────────────────────────────────────────╯
🚀 Crew: crew
└── 📋 Task: Data Product Planner
    Status: Executing Task...
    └── 🔍 Discovering available data products...
    └── 📊 Analyzing user intent...
    └── 🎯 Creating execution plan...
```

### Benefits of Enhanced System

1. **Intelligent Routing**: Automatically selects the most appropriate agent
2. **Contract-Driven**: All operations discovered from MCP registry
3. **Scalable**: Easy to add new data products without code changes
4. **Backward Compatible**: Existing simple agent continues to work
5. **Production Ready**: Real MCP integration with contract discovery

---

## ✅ Expected Takeaways
- **Metadata → API automation**: No manual schema or resolver code
- **GraphQL + OpenAPI contracts**: For interoperability
- **Production MCP integration**: Real AI agent communication
- **Enhanced Agent System**: Intelligent agent selection with CrewAI orchestration
- **Contract-driven operations**: All queries built from registry metadata
- **Three demo paths**: Basic, development, and advanced AI agent workflows
- **Works across domains**: Just change the YAML spec

---

## 🔁 Quick Reset Scripts

### Production MCP Demo Reset
```bash
# Stop any running services
pkill -f "uvicorn.*app.main" || true
pkill -f "mock_mcp.py" || true
pkill -f "http_server.py" || true

# Start GraphQL API
make run-graphql &
sleep 3

# Run production demo
make demo-prod
```

### HTTP MCP Demo Reset
```bash
# Stop any running services
pkill -f "uvicorn.*app.main" || true
pkill -f "mock_mcp.py" || true
pkill -f "http_server.py" || true

# Start GraphQL API
make run-graphql &
sleep 3

# Start HTTP MCP server
make run-mcp-http-server &
sleep 2

# Run HTTP demo
make demo-http
```

### Mock MCP Demo Reset
```bash
# Stop any running services
pkill -f "uvicorn.*app.main" || true
pkill -f "mock_mcp.py" || true
pkill -f "http_server.py" || true

# Start GraphQL API
make run-graphql &
sleep 3

# Run mock demo
make demo-mock
```

### Enhanced Agent Demo Reset
```bash
# Stop any running services
pkill -f "uvicorn.*app.main" || true
pkill -f "mock_mcp.py" || true
pkill -f "http_server.py" || true

# Start GraphQL API
make run-graphql &
sleep 3

# Test Enhanced Agent System
echo "Testing Simple Query (should use Simple Agent):"
python chat/agent_selector.py --ask "show payments for ACC-1002"

echo -e "\nTesting Complex Query (should use CrewAI Agent):"
python chat/agent_selector.py --ask "show me all customers in India with unpaid bills and their payment history"

echo -e "\nTesting CrewAI Components:"
python test_crewai.py
```

### Direct API Test
```bash
python - <<'PY'
import requests, json
q = "query { list_customers(limit:2){customer_id full_name} list_bills(limit:2){bill_id amount_due} }"
r = requests.post("http://127.0.0.1:8000/graphql", 
                  headers={"x-api-key": "dev-key"}, 
                  json={"query": q})
print(json.dumps(r.json(), indent=2))
PY
```

---

## 🔧 Troubleshooting

### Common Issues and Solutions

#### **1. GraphQL API Not Starting**
```bash
# Check if port 8000 is already in use
lsof -i :8000

# Kill any existing processes
pkill -f "uvicorn.*app.main"

# Restart the API
make run-graphql &
```

#### **2. CrewAI Import Errors**
```bash
# Ensure CrewAI is properly installed
pip install --upgrade crewai crewai-tools

# Check Python path
python -c "import crewai; print('CrewAI installed successfully')"
```

#### **3. MCP Server Connection Issues**
```bash
# Check environment variables
echo $TELECOM_API_BASE
echo $TELECOM_API_KEY

# Test stdio MCP server directly
python mcp_server/server.py --help

# Test HTTP MCP server
curl http://localhost:8001/
python mcp_server/http_server.py
```

#### **3a. HTTP MCP Server Issues**
```bash
# Check if port 8001 is available
lsof -i :8001

# Kill any existing HTTP MCP server
pkill -f "http_server.py"

# Start HTTP MCP server
make run-mcp-http-server

# Test HTTP endpoints
curl http://localhost:8001/
curl http://localhost:8001/tools
```

#### **4. Agent Selector Not Working**
```bash
# Check if all required files exist
ls -la chat/agent_selector.py
ls -la chat/simple_agent.py
ls -la chat/crewai_agent.py

# Test individual components
python chat/simple_agent.py --help
python chat/crewai_agent.py --help
```

#### **5. Well-Known Endpoints Not Accessible**
```bash
# Check if GraphQL API is running
curl -s http://localhost:8000/healthz

# Test well-known endpoints
curl -s http://localhost:8000/.well-known/telecom.registry.index
```

#### **6. Databricks Connection Issues**
```bash
# Test Databricks connectivity
python -c "
from databricks import sql
import os
conn = sql.connect(
    server_hostname=os.environ['DATABRICKS_SERVER_HOSTNAME'],
    http_path=os.environ['DATABRICKS_HTTP_PATH'],
    access_token=os.environ['DATABRICKS_TOKEN']
)
print('Databricks connection successful')
conn.close()
"
```

### **Debug Mode**

Enable verbose logging for troubleshooting:
```bash
# Set debug environment variable
export DEBUG=1

# Run with verbose output
python chat/agent_selector.py --ask "test query" --verbose
```

### **Reset Everything**

Complete system reset:
```bash
# Stop all services
pkill -f "uvicorn.*app.main" || true
pkill -f "mock_mcp.py" || true
pkill -f "http_server.py" || true
pkill -f "python.*agent" || true

# Clean up any lock files
rm -f *.lock

# Restart from scratch
make regen
make run-graphql &
sleep 5
make health
```

---

**End of file — demo_flow_runbook.md**

