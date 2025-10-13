# 📊 GraphQL Data Product Runtime — Architecture & Dataflow

This document provides a **visual overview** of the runtime’s architecture and dataflow using **Mermaid diagrams**, ready for inclusion in documentation portals or Markdown renderers that support Mermaid.

---

## 🔁 End-to-End Dataflow

```mermaid
sequenceDiagram
    autonumber
    participant D as Developer
    participant Git as Repo
    participant Gen as gen_registry_from_spec.py
    participant Reg as registry/*.yaml
    participant SG as schema_generator
    participant API as GraphQL Runtime (FastAPI + Ariadne)
    participant DB as Databricks SQL Warehouse
    participant Exp as export_contracts.py
    participant MCP as MCP / Agent Registry
    participant Ag as Agent / Client

    D->>Git: Edit dp/telecom.yml
    D->>Gen: make regen
    Gen->>Reg: Generate registry/*.yaml
    Gen->>SG: Stitch schema.graphql (SDL)
    D->>API: Run `uvicorn ... --env-file .env`
    API->>DB: Health check (SELECT 1)
    DB-->>API: OK

    D->>Exp: make export
    Exp->>Git: Write contracts/*.graphql + *.openapi.yaml
    Exp->>MCP: Register contracts via mcp_register_from_contracts.py

    note over MCP,Ag: Agents discover available data products and APIs

    Ag->>API: POST /graphql (list_customers, list_bills, ...)
    API->>DB: Execute SQL (expanded ${CATALOG}.${SCHEMA}.<table>)
    DB-->>API: Return rows
    API-->>Ag: JSON response
```

---

## 🧩 Component Architecture Overview

```mermaid
flowchart LR
  subgraph Dev["Developer Workflow"]
    Spec["dp/telecom.yml (Product Spec)"]
    Gen["gen_registry_from_spec.py"]
    Reg["registry/*.yaml (Runtime Metadata)"]
    SG["schema_generator.py"]
    Exp["export_contracts.py"]
    OAS["contracts/*.openapi.yaml"]
    SDL["contracts/*.graphql"]
    Man["contracts/manifest.json"]
    RegScript["mcp_register_from_contracts.py"]
  end

  subgraph Runtime["Runtime Environment"]
    API["FastAPI + Ariadne GraphQL Runtime"]
    RF["ResolverFactory (SQL Query Builder)"]
    Health["/health endpoint"]
  end

  subgraph Infra["External Systems"]
    DB[(Databricks SQL Warehouse)]
    MCP[(MCP / Agent Registry)]
    Agent[(Agent / Client)]
  end

  Spec --> Gen --> Reg --> SG --> API
  Reg --> Exp --> SDL
  Exp --> OAS --> Man --> RegScript --> MCP
  API --> RF --> DB
  API --> Health
  Agent --> MCP
  Agent --> API
  DB --> RF --> API --> Agent
```

---

## 🧠 Design Principles

1. **Spec-Driven Automation:**
   - Single YAML spec (`dp/telecom.yml`) defines entities, relationships, and filters.
   - No per-product Python code needed.

2. **Runtime Composition:**
   - Registry → Schema → Runtime → Contracts are all derived dynamically.
   - GraphQL schema built using Ariadne from registry metadata.

3. **Execution Model:**
   - Resolvers auto-generate SQL (templated `${CATALOG}.${SCHEMA}` references resolved at runtime).
   - Databricks SQL Warehouse serves as the live backend.

4. **Contract Management:**
   - `export_contracts.py` produces GraphQL SDL & OpenAPI specs.
   - Contracts registered to MCP for agent discovery.

5. **Observability:**
   - `/health` endpoint validates environment variables and Databricks connectivity.
   - Future: add metrics for query latency & row counts.

---

## ⚙️ Typical Command Flow

| Stage | Command | Outcome |
|--------|----------|----------|
| Spec → Registry | `make regen` | Generates `registry/*.yaml` and validates schema |
| Start Runtime | `uvicorn app.graphql_runtime_app:app --reload --env-file .env` | Launches GraphQL API runtime |
| Export Contracts | `make export` | Produces `.graphql` and `.openapi.yaml` contracts |
| Register to MCP | `make register` | Posts product metadata to MCP registry |
| Query Test | `python scripts/test_query.py` | Verifies end-to-end Databricks → GraphQL flow |

---

## 🧩 Components Summary

| Component | Description |
|------------|-------------|
| **dp/telecom.yml** | Source spec for defining data products and entities |
| **gen_registry_from_spec.py** | Translates spec to runtime registry YAMLs |
| **schema_generator.py** | Builds GraphQL schema (SDL) dynamically |
| **graphql_runtime_app.py** | Starts runtime app using FastAPI + Ariadne |
| **resolver_factory.py** | Converts GraphQL requests → Databricks SQL queries |
| **export_contracts.py** | Emits OpenAPI + SDL contracts for each product |
| **mcp_register_from_contracts.py** | Registers contracts into MCP registry |
| **mock_mcp.py** | Lightweight mock MCP registry for local demo |

---

✅ **Outcome:** Fully metadata-driven GraphQL runtime, contract-aware, and MCP-registrable — with zero manual coding per data product.

**End of file — architecture_and_dataflow.md**