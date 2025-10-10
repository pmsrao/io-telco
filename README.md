# Telecom GraphQL — Dynamic-first (v3)

A metadata-driven GraphQL API that exposes Databricks-hosted Telecom Data Products through a dynamic schema generated from YAML registry files. The system includes an MCP (Model Context Protocol) server for agent integration and a CLI agent for natural language queries.

## Architecture Overview

- **Dynamic GraphQL API**: Schema generated at runtime from `registry/*.yaml` metadata
- **Databricks Integration**: Direct connection to Unity Catalog/SQL Warehouse
- **MCP Server**: Exposes `telecom.graphql.run` tool for agent integration
- **CLI Agent**: Natural language to GraphQL query translation
- **Registry-First**: Zero per-DP code, all configuration via YAML

## Quick Start

### 1. Prerequisites
- Python 3.8+
- Databricks workspace with Unity Catalog access
- Make (for convenient commands)

### 2. Installation
```bash
# Clone and setup
git clone <repository>
cd telecom-graphql-dynamic-v3

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

### 4. Run the System

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

### 5. Verify Installation
```bash
# Check health
make health
# Expected: {"ok":true,"mode":"dynamic"}

# Test GraphQL introspection (requires API key)
curl -s -H "x-api-key: dev-key" -H "Content-Type: application/json" \
  -d '{"query":"{ __schema { queryType { fields { name } } } }"}' \
  "http://localhost:8080/graphql" | jq
```

## Demo Scenarios

### 1. Direct GraphQL Queries
```bash
# List payments
curl -s -H "x-api-key: dev-key" -H "Content-Type: application/json" \
  -d '{"query":"{ list_payments(limit:5){ payment_id amount status created_at } }"}' \
  "http://localhost:8080/graphql" | jq

# Get specific payment
curl -s -H "x-api-key: dev-key" -H "Content-Type: application/json" \
  -d '{"query":"{ get_payment(payment_id:\"PAY-001\"){ payment_id amount status } }"}' \
  "http://localhost:8080/graphql" | jq
```

### 2. MCP Integration
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
- "show POSTED payments for ACC-1002 in the last 30 days"
- "get bill BILL-9001 and list its payments"

## Available Commands

```bash
make help          # Show all available commands
make install       # Install dependencies
make run-graphql   # Start GraphQL API server
make health        # Check API health
make mcp-call      # Test MCP integration
make demo          # Run agent demo
make print-env     # Show effective environment variables
```

## Registry Configuration

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
    filters:
      - { name: account_id, type: STRING, operator: "=" }
      - { name: status, type: STRING, operator: "=" }
      - { name: from_time, type: TIMESTAMP, operator: ">=", column: created_at }
      - { name: to_time, type: TIMESTAMP, operator: "<=", column: created_at }
relationships: []
```

## API Endpoints

- `GET /healthz` - Health check
- `POST /graphql` - GraphQL endpoint (requires `x-api-key` header)

## Development

### Adding New Data Products
1. Create a new YAML file in `registry/`
2. Define entities, filters, and relationships
3. Restart the GraphQL server
4. The schema will automatically include your new entities

### Custom Queries
The system supports various filter operators:
- `=, !=, >, >=, <, <=` - Standard comparisons
- `ilike` - Case-insensitive pattern matching
- `ilike_any` - Multi-column search

## Troubleshooting

### Common Issues
1. **Connection Errors**: Verify Databricks credentials in `.env`
2. **Schema Issues**: Check registry YAML syntax
3. **MCP Errors**: Ensure API_KEY is set correctly

### Debug Commands
```bash
make print-env     # Check environment variables
make health        # Verify API is running
curl -v http://localhost:8080/healthz  # Detailed health check
```

## Architecture Details

See `docs/architecture.md` for comprehensive system design, including:
- Component interactions
- Data flow diagrams
- Security considerations
- Future roadmap
