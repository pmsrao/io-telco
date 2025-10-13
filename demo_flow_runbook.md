# 📘 Demo Flow — GraphQL Data Product Runtime

This markdown captures the **end-to-end demo flow** for the Telecom Data Product runtime — from spec to live API, complete with narrative points that can be spoken during a demo session.

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

### 🧱 4️⃣ (Optional) Start mock MCP server
If you don’t have a live MCP server, run the local mock one:
```bash
python scripts/mock_mcp.py &
```
Expected output: `🚀 Mock MCP server running on http://127.0.0.1:9000`

Now you’re ready for the full demo run.

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

**Talking point:** “From the product spec, we automatically infer entities, relationships, and filters — these are persisted as registry metadata used at runtime.”

---

### 2️⃣ Start GraphQL runtime
```bash
uvicorn app.graphql_runtime_app:app --reload --env-file .env
```
**Purpose:** Starts metadata-driven runtime that builds schema and resolvers dynamically.

**Check health:**
```bash
curl http://127.0.0.1:8000/health
```
✅ Expected: `{ "ok": true, "db": "ok" }`

**Talking point:** “The runtime loads the registry, constructs GraphQL schema, wires resolvers to Databricks SQL, and verifies connectivity.”

---

### 3️⃣ Export contracts (OpenAPI + SDL)
```bash
make export
```
**Purpose:** Emits per-product contracts to `contracts/`, e.g. `contracts/customer.graphql`, `contracts/payments.openapi.yaml`.

**Talking point:** “These are self-describing contracts — standard GraphQL SDL and OpenAPI definitions — which external systems or agents can introspect or generate clients from.”

---

### 4️⃣ Register contracts with MCP (mock or real)

**Option A — with real MCP**
```bash
export MCP_URL=https://mcp-server/register
make register
```

**Option B — local mock MCP**
```bash
python scripts/mock_mcp.py &
export MCP_URL=http://127.0.0.1:9000/register
make register
```
✅ Expected: `{"status":"ok","name":"customer"}` and `{"status":"ok","name":"payments"}`

**Talking point:** “Now the MCP (agent registry) knows about our Data Products and their GraphQL contracts — enabling agents or other systems to discover and invoke them dynamically.”

---

### 5️⃣ Query via GraphQL API
```bash
python - <<'PY'
import requests, json
q = """
query {
  list_customers(limit: 5) { customer_id full_name status }
  list_bills(limit: 5) { bill_id amount_due status }
}
"""
r = requests.post("http://127.0.0.1:8000/graphql", json={"query": q})
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

**Talking point:** “This query runs live against Databricks SQL — no hand-written resolvers, all metadata-driven.”

---

### 6️⃣ Bonus — Modify spec and regenerate

**Change something in** `dp/telecom.yml` (e.g., add a filter or alias) → then rerun:
```bash
make all
```

**Talking point:** “We can evolve the product definition declaratively. The contracts, schema, and registry all stay consistent automatically.”

---

## 🧩 Services Running During Demo
| Component | Purpose | Port |
|------------|----------|------|
| GraphQL Runtime | Metadata-driven API layer | `8000` |
| Databricks SQL Warehouse | Actual data backend | remote |
| MCP (mock or real) | Contract registry for agents | `9000` |

---

## ✅ Expected Takeaways
- Metadata → API automation: no manual schema or resolver code.
- GraphQL + OpenAPI contracts for interoperability.
- MCP integration for agent discovery.
- Works across domains — just change the YAML spec.

---

## 🔁 Quick Reset Script
```bash
pkill -f "uvicorn .*graphql_runtime_app" || true
uvicorn app.graphql_runtime_app:app --reload --env-file .env &
sleep 2
make all
python - <<'PY'
import requests, json
q = "query { list_customers(limit:2){customer_id full_name} list_bills(limit:2){bill_id amount_due} }"
print(json.dumps(requests.post("http://127.0.0.1:8000/graphql", json={"query": q}).json(), indent=2))
PY
```

---

**End of file — demo_flow_runbook.md**

