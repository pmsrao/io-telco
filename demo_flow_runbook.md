# 📘 Demo Flow — GraphQL Data Product Runtime

This markdown captures the **end-to-end demo flow** for the Telecom Data Product runtime — from spec to live API, complete with narrative points that can be spoken during a demo session.

## 🎯 Demo Paths Available

This system supports **two distinct demo paths**:

1. **🚀 Production MCP Demo** (`make demo-prod`) - Uses the real MCP server for AI agent communication
2. **🧪 Mock MCP Demo** (`make demo-mock`) - Uses mock registry for contract registration + production MCP for agent communication

Both paths demonstrate the same core functionality but with different MCP components.

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

**For Production MCP Demo:**
- No additional setup needed - the production MCP server (`mcp_server/server.py`) will be used automatically
- This server communicates with AI agents via stdio protocol

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

#### 🚀 **Path A: Production MCP Demo** (Recommended)
```bash
make demo-prod
```
**What happens:**
- Uses the production MCP server (`mcp_server/server.py`) for AI agent communication
- Demonstrates real MCP protocol communication via stdio
- Shows natural language → GraphQL query translation
- **No contract registration needed** - direct agent communication

**Talking point:** "This demonstrates the production MCP server in action - AI agents can directly communicate with our GraphQL API using the MCP protocol."

#### 🧪 **Path B: Mock MCP Demo** (Development/Testing)
```bash
make demo-mock
```
**What happens:**
- Starts mock MCP registry on port 9000
- Registers contracts with the mock registry
- Uses production MCP server for agent communication
- Shows complete contract registration workflow

**Talking point:** "This shows the complete workflow including contract registration with an MCP registry, followed by agent communication."

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
r = requests.post("http://127.0.0.1:8080/graphql", 
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

## 🧩 Services Running During Demo

### 🚀 Production MCP Demo
| Component | Purpose | Port/Protocol |
|------------|----------|---------------|
| GraphQL Runtime | Metadata-driven API layer | `8080` |
| Databricks SQL Warehouse | Actual data backend | remote |
| Production MCP Server | AI agent communication | stdio protocol |
| CLI Agent | Natural language → GraphQL | local process |

### 🧪 Mock MCP Demo
| Component | Purpose | Port/Protocol |
|------------|----------|---------------|
| GraphQL Runtime | Metadata-driven API layer | `8080` |
| Databricks SQL Warehouse | Actual data backend | remote |
| Mock MCP Registry | Contract registration | `9000` |
| Production MCP Server | AI agent communication | stdio protocol |
| CLI Agent | Natural language → GraphQL | local process |

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
TELECOM_API_BASE=http://localhost:8080    # Your GraphQL API base URL
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

## ✅ Expected Takeaways
- **Metadata → API automation**: No manual schema or resolver code
- **GraphQL + OpenAPI contracts**: For interoperability
- **Production MCP integration**: Real AI agent communication
- **Dual demo paths**: Production vs development workflows
- **Works across domains**: Just change the YAML spec

---

## 🔁 Quick Reset Scripts

### Production MCP Demo Reset
```bash
# Stop any running services
pkill -f "uvicorn.*app.main" || true
pkill -f "mock_mcp.py" || true

# Start GraphQL API
make run-graphql &
sleep 3

# Run production demo
make demo-prod
```

### Mock MCP Demo Reset
```bash
# Stop any running services
pkill -f "uvicorn.*app.main" || true
pkill -f "mock_mcp.py" || true

# Start GraphQL API
make run-graphql &
sleep 3

# Run mock demo
make demo-mock
```

### Direct API Test
```bash
python - <<'PY'
import requests, json
q = "query { list_customers(limit:2){customer_id full_name} list_bills(limit:2){bill_id amount_due} }"
r = requests.post("http://127.0.0.1:8080/graphql", 
                  headers={"x-api-key": "dev-key"}, 
                  json={"query": q})
print(json.dumps(r.json(), indent=2))
PY
```

---

**End of file — demo_flow_runbook.md**

