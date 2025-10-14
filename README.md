# Telecom Data Products — GraphQL + MCP Runtime

A **metadata-driven GraphQL API** that exposes Databricks-hosted Telecom Data Products through a dynamic schema generated from YAML registry files. The system includes an MCP (Model Context Protocol) server for AI agent integration and a CLI agent for natural language queries.

## 🏗️ Architecture Overview

This system implements a **registry-first approach** where Data Products are defined once in YAML and automatically exposed as GraphQL APIs with full AI agent integration:

- **📊 Data Products**: Defined in `dp/telecom.yml` with entities, relationships, and filters
- **🔧 Registry System**: Runtime metadata in `registry/*.yaml` drives GraphQL schema generation
- **🚀 Dynamic GraphQL API**: Schema and resolvers generated at startup from registry metadata
- **🔗 Databricks Integration**: Direct connection to Unity Catalog/SQL Warehouse
- **🤖 MCP Server**: Exposes `telecom.graphql.run` tool for AI agent integration
- **💬 CLI Agent**: Natural language to GraphQL query translation
- **⚡ Zero Code**: No per-Data-Product code required, all configuration via YAML

## 🚀 Quick Start

### 1. Prerequisites
- **Python 3.8+**
- **Databricks workspace** with Unity Catalog access
- **Make** (for convenient commands)

### 2. Installation
```bash
# Clone and setup
git clone <repository>
cd io-telco

# Install dependencies
make install
```

### 3. Configuration
Create a `.env` file with your Databricks credentials:

```bash
# Databricks Configuration
DATABRICKS_HOST=your-databricks-host
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/your-warehouse-id
DATABRICKS_TOKEN=your-databricks-token

# Catalog/Schema (used in registry table strings)
CATALOG=your_catalog
SCHEMA=your_schema

# API Configuration
API_KEY=dev-key
API_BASE=http://localhost:8080
GQL_PATH=/graphql

# MCP/Agent Configuration
TELECOM_API_BASE=http://localhost:8080
TELECOM_GQL_PATH=/graphql
TELECOM_API_KEY=dev-key
```

### 4. Generate Registry from Data Products
```bash
# Generate registry YAMLs from master specification
python scripts/gen_registry_from_spec.py dp/telecom.yml registry/ --verbose

# Or bootstrap from existing Databricks tables
python scripts/gen_registry_bootstrap.py --catalog your_catalog --schema your_schema --out registry
```

### 5. Run the System

#### Option A: Using Make (Recommended)
```bash
# Start the GraphQL API
make run-graphql
```

#### Option B: Manual Start
```bash
# Load environment variables
export $(cat .env | xargs)

# Start the server
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

### 6. Verify Installation
```bash
# Check health
make health
# Expected: {"ok":true,"mode":"dynamic"}

# Test GraphQL introspection (requires API key)
curl -s -H "x-api-key: dev-key" -H "Content-Type: application/json" \
  -d '{"query":"{ __schema { queryType { fields { name } } } }"}' \
  "http://localhost:8080/graphql" | jq
```

## 🎯 Demo Scenarios

### 1. Direct GraphQL Queries
```bash
# List payments with filters
curl -s -H "x-api-key: dev-key" -H "Content-Type: application/json" \
  -d '{"query":"{ list_payments(limit:5){ payment_id amount status created_at } }"}' \
  "http://localhost:8080/graphql" | jq

# Get specific payment by ID
curl -s -H "x-api-key: dev-key" -H "Content-Type: application/json" \
  -d '{"query":"{ get_payment(payment_id:\"PAY-001\"){ payment_id amount status } }"}' \
  "http://localhost:8080/graphql" | jq

# List customers with search
curl -s -H "x-api-key: dev-key" -H "Content-Type: application/json" \
  -d '{"query":"{ list_customers(filters:{q:\"rao\"}, limit:10){ customer_id full_name primary_email } }"}' \
  "http://localhost:8080/graphql" | jq
```

### 2. MCP Integration (AI Agent Tool)
```bash
# One-off MCP call
make mcp-call
```

### 3. Agent Demo (Natural Language)
```bash
# Run the full demo with natural language queries
make demo
```

This will demonstrate:
- **"show POSTED payments for ACC-1002 in the last 30 days"**
- **"get bill BILL-9001 and list its payments"**

## 🛠️ Available Commands

```bash
make help          # Show all available commands
make install       # Install dependencies
make run-graphql   # Start GraphQL API server
make health        # Check API health
make mcp-call      # Test MCP integration
make demo          # Run agent demo
make print-env     # Show effective environment variables
```

## 📋 Registry Configuration

The system uses YAML files in the `registry/` directory to define data products. Each file describes:
- **Entities**: Tables and their GraphQL types
- **Filters**: Query parameters and SQL operators
- **Relationships**: (vNext) Nested field definitions

Example `registry/payments.yaml`:
```yaml
data_product: payments
entities:
  payments:
    table: "${CATALOG}.${SCHEMA}.payments"
    key: payment_id
    columns:
      payment_id: { scalar: String }
      account_id: { scalar: String }
      amount: { scalar: Decimal }
      status: { scalar: String }
      created_at: { scalar: Timestamp }
    filters: []
    aliases:
      - get_payment
      - list_payments
    order_by_default: -created_at
    pagination:
      default_limit: 50
      max_limit: 500
    policy:
      required_window: false
```

## 🔌 API Endpoints

- `GET /healthz` - Health check
- `POST /graphql` - GraphQL endpoint (requires `x-api-key` header)

## 🏗️ System Architecture

### Data Flow
```
Data Products (dp/telecom.yml) 
    ↓ [scripts/gen_registry_from_spec.py]
Registry YAMLs (registry/*.yaml)
    ↓ [app/runtime/schema_generator.py + resolver_factory.py]
GraphQL Schema + Resolvers
    ↓ [FastAPI + Ariadne/Strawberry]
GraphQL API (/graphql)
    ↓ [MCP Server]
AI Agent Integration (telecom.graphql.run tool)
```

### Key Components
- **`app/runtime/schema_generator.py`** - Converts registry metadata to GraphQL SDL
- **`app/runtime/resolver_factory.py`** - Creates SQL resolvers with filter compilation
- **`app/runtime/registry_loader.py`** - Loads and normalizes YAML metadata
- **`mcp_server/server.py`** - Exposes `telecom.graphql.run` tool for agents
- **`chat/agent.py`** - Natural language → GraphQL query translation

## 🚀 Development

### Adding New Data Products
1. **Define in master spec**: Add to `dp/telecom.yml`
2. **Generate registry**: Run `python scripts/gen_registry_from_spec.py dp/telecom.yml registry/`
3. **Restart server**: The schema will automatically include your new entities

### Custom Queries
The system supports various filter operators:
- `=, !=, >, >=, <, <=` - Standard comparisons
- `ilike` - Case-insensitive pattern matching
- `ilike_any` - Multi-column search

## 🐛 Troubleshooting

### Common Issues
1. **Connection Errors**: Verify Databricks credentials in `.env`
2. **Schema Issues**: Check registry YAML syntax
3. **MCP Errors**: Ensure API_KEY is set correctly

### Debug Commands
```bash
make print-env     # Check environment variables
make health        # Verify API is running
curl -v http://localhost:8000/healthz  # Detailed health check
```

## 📚 Architecture Details

See `docs/architecture.md` for comprehensive system design, including:
- Component interactions
- Data flow diagrams
- Security considerations
- Future roadmap

## 🧹 Repository Cleanup

The following files are **redundant** and can be safely removed:
- `app/schema_static.py` - Static schema (unused, system is fully dynamic)
- `app/meta_graphql.py` - Alternative GraphQL implementation (unused)
- `app/graphql_runtime_app.py` - Alternative FastAPI app (unused)
- `app/runtime/observability.py` - Basic observability (unused)
- `app/runtime/operator_compiler.py` - Filter compiler (unused)
- `app/runtime/policy_compiler.py` - Policy engine (unused)
- `app/runtime/sql_builder.py` - SQL builder (unused)
- `app/runtime/type_maps.py` - Type mappings (unused)
