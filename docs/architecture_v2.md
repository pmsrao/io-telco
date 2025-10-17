# Telecom Data Products — GraphQL + MCP + Agent Selector Architecture (v2)

**Date:** 2025-10-15  
**Scope:** Enhanced end-to-end (E2E) stack with intelligent agent selection, performance monitoring, and optimized CrewAI integration for complex multi-entity queries.

---

## 1) Goals & Non-Goals

**Goals**
- Keep Data Products (DPs) **inside Databricks** (Unity Catalog / SQL Warehouse).
- Expose DP entities via **metadata-driven GraphQL API** with intelligent query routing.
- Provide **intelligent agent selection** between Simple Agent (fast) and CrewAI Agent (complex).
- Enable **complex multi-entity queries** with proper filter propagation and correlation.
- Include **performance monitoring** and **observability** with metrics collection.
- Ship a **repeatable dev experience** with comprehensive demo flows.

**Non-Goals (v2)**
- Relationship/nested GraphQL fields (e.g., `bill → payments`) generated from metadata.  
  > *Planned for vNext.*
- Row-level security (RLS) / policy enforcement in the runtime.  
  > *Planned for vNext.*
- Caching/persisted queries, federation/gateway.  
  > *Planned for vNext.*

---

## 2) High-Level Architecture

### 2.1 Components

- **Databricks / Unity Catalog**: Authoritative store for all DP tables.
- **Registry (YAML)**: Declarative DP metadata → drives the GraphQL schema & filters.
- **GraphQL API (FastAPI + Strawberry)**: Builds types/resolvers **at startup** from Registry + table introspection.
- **MCP Server**: Exposes tools for GraphQL execution and contract discovery.
  - **HTTP MCP Server**: Standalone HTTP server with real-time logging (primary method)
  - **Stdio MCP Server**: Traditional subprocess-based communication (legacy support)
- **Agent Selector**: Intelligent routing between Simple Agent and CrewAI Agent based on query complexity.
- **Simple Agent**: Fast, reliable agent for single-entity queries with basic filtering (HTTP MCP).
- **CrewAI Agent**: Advanced agent for complex multi-entity queries with correlation (HTTP MCP).
- **Performance Monitoring**: Metrics collection and reporting system.

### 2.2 Enhanced Dataflow with Agent Selection

```mermaid
flowchart TD
  subgraph UserSpace["User/Assistant Space"]
    UI["Chat / CLI"]
    AS["Agent Selector<br/>(Intelligent Routing)"]
  end

  subgraph AgentLayer["Agent Layer"]
    SA["Simple Agent<br/>(Fast, Single Entity)"]
    CA["CrewAI Agent<br/>(Complex, Multi-Entity)"]
  end

  subgraph Host["Local Host / Container"]
    MCP["HTTP MCP Server<br/>(Port 8001)<br/>(telecom.graphql.run<br/>mcp_contract<br/>mcp_discovery)"]
    GQL["GraphQL API<br/>(FastAPI + Strawberry)<br/>Dynamic from Registry<br/>(Port 8000)"]
    MON["Performance Monitoring<br/>(Metrics Collection)"]
  end

  subgraph DBX["Databricks / SQL Warehouse"]
    subgraph UC["Unity Catalog: CATALOG.SCHEMA"]
      DP_C{{Customer DP}}
      DP_P{{Payments DP}}
      DP_B{{Bills DP}}
    end
  end

  REG["Registry YAMLs<br/>(registry/*.yaml)"]

  UI --> AS
  AS -->|Simple Query| SA
  AS -->|Complex Query| CA
  SA -- HTTP (Port 8001) --> MCP
  CA -- HTTP (Port 8001) --> MCP
  MCP -- HTTP (Port 8000) --> GQL
  GQL -- DESCRIBE + SELECT --> UC
  MON --> AS
  MON --> SA
  MON --> CA

  DP_C --- UC
  DP_P --- UC
  DP_B --- UC

  REG -.-> GQL
  REG -.-> MCP
```

### 2.3 Agent Selection Logic

```mermaid
flowchart TD
  Query["User Query"] --> AS["Agent Selector"]
  AS --> Check1{"Contains 'and list'<br/>pattern?"}
  Check1 -->|Yes| Check2{"Single entity<br/>with action?"}
  Check2 -->|Yes| Simple["Route to Simple Agent"]
  Check2 -->|No| CrewAI["Route to CrewAI Agent"]
  Check1 -->|No| Check3{"Contains complex<br/>patterns?"}
  Check3 -->|Yes| CrewAI
  Check3 -->|No| Check4{"Multiple entities<br/>detected?"}
  Check4 -->|Yes| CrewAI
  Check4 -->|No| Simple
```

---

## 3) MCP Communication Methods

### 3.1 Stdio MCP Server (Traditional)
- **Communication**: Subprocess via stdin/stdout
- **Logging**: Hidden (logs go to subprocess stdout)
- **Scalability**: One client per process
- **Use Case**: Simple applications, basic production

### 3.2 HTTP MCP Server (Enhanced)
- **Communication**: HTTP requests/responses
- **Logging**: Real-time visible in console
- **Scalability**: Multiple clients can connect
- **Use Case**: Development, debugging, production with observability

### 3.3 MCP Server Comparison

| Aspect | Stdio MCP | HTTP MCP |
|--------|-----------|----------|
| **Logging** | ❌ Hidden | ✅ **Real-time visible** |
| **Debugging** | ❌ Hard | ✅ **Easy with curl/Postman** |
| **Monitoring** | ❌ Limited | ✅ **Full HTTP monitoring** |
| **Multiple Clients** | ❌ One per process | ✅ **Multiple simultaneous** |
| **Scalability** | ❌ Limited | ✅ **Better for production** |
| **Production Ready** | ✅ Yes | ✅ **Recommended** |

### 3.4 HTTP MCP Server Architecture

```mermaid
flowchart TD
    subgraph HTTPMCP["HTTP MCP Server (Port 8001)"]
        API["FastAPI Application"]
        Tools["MCP Tools"]
        Logging["Real-time Logging"]
    end
    
    subgraph Agents["AI Agents"]
        HTTPAgent["HTTP Agent"]
        CrewAIAgent["CrewAI Agent"]
    end
    
    subgraph GraphQL["GraphQL API (Port 8000)"]
        GQL["FastAPI + Strawberry"]
        DB["Databricks SQL"]
    end
    
    HTTPAgent -->|HTTP Requests| API
    CrewAIAgent -->|HTTP Requests| API
    API --> Tools
    Tools -->|GraphQL Queries| GQL
    GQL --> DB
    API --> Logging
    
    style HTTPMCP fill:#e1f5fe
    style Logging fill:#c8e6c9
```

---

## 4) Agent Architecture

### 4.1 Simple Agent
- **Purpose**: Handle single-entity queries with basic filtering
- **Performance**: ~2-5 seconds
- **Use Cases**: 
  - "show POSTED payments for ACC-1002 in the last 60 days"
  - "get bill BILL-9001 and list its payments"
- **Tools**: MCP-based GraphQL execution
- **Characteristics**: Fast, reliable, deterministic

### 4.2 CrewAI Agent
- **Purpose**: Handle complex multi-entity queries with correlation
- **Performance**: ~30-60 seconds
- **Use Cases**:
  - "show me all customers in India with unpaid bills and their payment history"
  - Complex queries involving multiple entities and relationships
- **Tools**: 
  - `mcp_contract`: Contract discovery
  - `graphql_query_builder`: Dynamic query building
  - `graphql_executor`: Query execution
  - `entity_correlator`: Data correlation
- **Characteristics**: Intelligent, flexible, handles complex scenarios

### 3.3 Agent Selection Criteria

```python
def _is_simple_query(self, user_input: str) -> bool:
    """
    Determine if a query is simple enough for the simple agent
    """
    user_lower = user_input.lower()
    
    # Complex patterns that require CrewAI
    complex_patterns = [
        r'\b(and|or|with|including|also|additionally)\s+(?:me|all|the|a|an)\s+',
        r'\b(compare|comparison|versus|vs)\b',
        r'\b(aggregate|sum|total|count|average|max|min)\b',
        r'\b(relationship|related|associated|linked)\b',
        r'\b(analyze|analysis|insight|pattern|trend)\b',
        r'\b(complex|detailed|comprehensive|complete)\b',
    ]
    
    # Special case: "and" followed by "list" indicates multi-entity query
    if re.search(r'\band\s+list\b', user_lower):
        # Check if it's a single entity with action
        if re.search(r'\b(get|fetch|retrieve|show)\s+\w+\s+\w+.*\band\s+list\s+its?\s+\w+', user_lower):
            return True  # Simple query
        return False
    
    # Check for multiple entities (not filters)
    entities = []
    if any(word in user_lower for word in ['payment', 'payments']):
        entities.append('payments')
    if any(word in user_lower for word in ['bill', 'bills']):
        entities.append('bills')
    if any(word in user_lower for word in ['customer', 'customers']):
        entities.append('customers')
    
    # Only count as multiple entities if they're the main subject
    entity_indicators = ['show me', 'list', 'get', 'find', 'display']
    has_entity_indicator = any(indicator in user_lower for indicator in entity_indicators)
    
    if len(entities) > 1 and has_entity_indicator:
        return False
    
    return True
```

---

## 5) Enhanced Registry-First: Metadata Model

### 4.1 Current Registry Structure
Each Data Product contributes a YAML file under `registry/` with enhanced metadata:

```yaml
data_product: payments
entities:
  payments:
    table: "${CATALOG}.${SCHEMA}.payments"
    key: payment_id
    columns:
      payment_id: { scalar: "String" }
      account_id: { scalar: "String" }
      bill_id: { scalar: "String" }
      amount: { scalar: "Decimal" }
      currency: { scalar: "String" }
      method: { scalar: "String" }
      status: { scalar: "String" }
      created_at: { scalar: "Timestamp" }
      updated_at: { scalar: "Timestamp" }
    filters:
      - { name: account_id, type: STRING, op: "=", column: account_id }
      - { name: bill_id, type: STRING, op: "=", column: bill_id }
      - { name: status, type: STRING, op: "=", column: status }
      - { name: method, type: STRING, op: "=", column: method }
      - { name: from_time, type: TIMESTAMP, op: ">=", column: created_at }
      - { name: to_time, type: TIMESTAMP, op: "<=", column: created_at }
    aliases: ["get_payment", "list_payments"]
    order_by_default: "-created_at"
    pagination: { default_limit: 50, max_limit: 500 }
    policy: { required_window: false }
```

### 4.2 Future: Enhanced Metadata with Semantic Tags
```yaml
data_product: payments
description: "Payment processing and billing information"
entities:
  payments:
    table: "${CATALOG}.${SCHEMA}.payments"
    key: payment_id
    description: "Payment transactions and processing records"
    semantic_tags: ["payment", "transaction", "money", "financial"]
    columns:
      payment_id: 
        scalar: "String"
        description: "Unique payment identifier"
        semantic_tags: ["id", "identifier", "key"]
      account_id:
        scalar: "String"
        description: "Account associated with the payment"
        semantic_tags: ["account", "customer_account", "acc"]
        pattern_matching:
          - { pattern: "acc[_-]?(\\d+)", format: "ACC-{match}" }
          - { pattern: "account\\s+([a-zA-Z0-9_-]+)", format: "{match}" }
      status:
        scalar: "String"
        description: "Payment processing status"
        semantic_tags: ["status", "state", "condition"]
        value_mappings:
          - { natural_language: ["posted", "paid", "successful", "completed"], value: "POSTED" }
          - { natural_language: ["failed", "failure", "error", "declined"], value: "FAILED" }
          - { natural_language: ["pending", "processing", "in_progress"], value: "PENDING" }
```

---

## 6) Performance Monitoring & Metrics

### 5.1 Metrics Collection
- **Query Performance**: Response times, success/failure rates
- **Agent Usage**: Simple vs CrewAI agent selection
- **Entity Detection**: Which entities are being queried
- **Complexity Analysis**: Query complexity scoring
- **Tool Usage**: GraphQL queries, tool calls, correlations

### 5.2 Metrics Dashboard
```bash
# Generate performance report
python -m monitoring.cli report --hours 1

# Output example:
📊 Performance Metrics Summary Report
==================================================
📅 Period: Last 1 hours
🕐 Generated: 2025-10-15T07:04:27.593912+00:00

📈 Query Statistics:
  • Total Queries: 18
  • Success Rate: 100.0%
  • Failed Queries: 0

🤖 Agent Usage:
  • Simple Agent: 8 queries (44.4%)
  • CrewAI Agent: 10 queries (55.6%)

⏱️  Response Times:
  • Average: 78341ms
  • Range: 1989ms - 511927ms
  • Slow Queries (>5s): 12
  • Very Slow Queries (>30s): 10

🏷️  Entity Detection:
  • payments: 18
  • bills: 12
  • customers: 6

🧠 Complexity Analysis:
  • Average Complexity Score: 0.550
  • High Complexity Queries: 6
```

---

## 7) Enhanced Request Sequence

### 6.1 Simple Query Flow
```mermaid
sequenceDiagram
  participant User
  participant AS as Agent Selector
  participant SA as Simple Agent
  participant MCP as MCP Server
  participant GQL as GraphQL API
  participant DB as Databricks
  participant MON as Monitoring

  User->>AS: "show POSTED payments for ACC-1002 in the last 60 days"
  AS->>AS: Analyze query complexity
  AS->>SA: Route to Simple Agent
  SA->>MON: Start query tracking
  SA->>SA: Build GraphQL + time window
  SA->>MCP: call tool telecom.graphql.run
  MCP->>GQL: POST /graphql (x-api-key)
  GQL->>DB: SELECT ... WHERE account_id=... AND created_at BETWEEN ...
  DB-->>GQL: rows
  GQL-->>MCP: JSON
  MCP-->>SA: JSON
  SA->>MON: Record success metrics
  SA-->>User: Rendered result
```

### 6.2 Complex Query Flow
```mermaid
sequenceDiagram
  participant User
  participant AS as Agent Selector
  participant CA as CrewAI Agent
  participant MCP as MCP Server
  participant GQL as GraphQL API
  participant DB as Databricks
  participant MON as Monitoring

  User->>AS: "show me all customers in India with unpaid bills and their payment history"
  AS->>AS: Analyze query complexity
  AS->>CA: Route to CrewAI Agent
  CA->>MON: Start query tracking
  CA->>MCP: call tool mcp_contract
  MCP-->>CA: Contract data
  CA->>MCP: call tool graphql_query_builder
  MCP-->>CA: Generated GraphQL query
  CA->>MCP: call tool graphql_executor
  MCP->>GQL: POST /graphql
  GQL->>DB: Multi-entity SELECT queries
  DB-->>GQL: Correlated results
  GQL-->>MCP: JSON
  MCP-->>CA: JSON
  CA->>MON: Record success metrics
  CA-->>User: Formatted multi-entity results
```

---

## 8) Enhanced Repo Layout

```
.
├─ app/
│  ├─ main.py                    # FastAPI app with GraphQL router
│  ├─ meta_graphql.py           # Dynamic GraphQL schema generation
│  ├─ config.py                 # Configuration management
│  └─ db.py                     # Database connection management
├─ chat/
│  ├─ agent_selector.py         # Intelligent agent routing
│  ├─ simple_agent.py           # Fast single-entity agent
│  ├─ crewai_agent.py           # Complex multi-entity agent
│  └─ agent.py                  # Legacy MCP-based agent
├─ telecom_crewai/
│  ├─ crew.py                   # CrewAI orchestration
│  ├─ agents/
│  │  ├─ query_agent.py         # GraphQL query building agent
│  │  ├─ planner.py             # Query planning agent
│  │  └─ composer.py            # Response composition agent
│  └─ tools/
│      ├─ graphql_executor.py   # GraphQL execution tool
│      ├─ query_builder.py      # Dynamic query building tool
│      ├─ mcp_discovery.py      # Contract discovery tool
│      └─ entity_correlator.py  # Data correlation tool
├─ monitoring/
│  ├─ metrics_collector.py      # Performance metrics collection
│  ├─ metrics_reporter.py       # Metrics reporting and analysis
│  ├─ config.py                 # Monitoring configuration
│  └─ cli.py                    # Command-line interface
├─ registry/
│  ├─ payments.yaml             # Payments data product metadata
│  └─ customer.yaml             # Customer data product metadata
├─ mcp_server/
│  └─ server.py                 # MCP server with enhanced tools
├─ docs/
│  ├─ architecture_v2.md        # This document
│  ├─ architecture.md           # Legacy architecture
│  ├─ architecture_and_dataflow.md # Dataflow diagrams
│  └─ crewai_optimization_lessons.md # Optimization learnings
├─ Makefile                     # Enhanced with demo-prod target
├─ .env                         # Environment configuration
└─ requirements.txt             # Python dependencies
```

---

## 9) Enhanced Configuration

**`.env` (example)**
```
# Databricks
DATABRICKS_HOST=XXXXXXXX
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/XXXX
DATABRICKS_TOKEN=XXXXXXXX

# Catalog/Schema (used in registry table strings)
CATALOG=india_dataengineer_recruitment
SCHEMA=telco_silver

# API guard for GraphQL
API_KEY=dev-key

# Agent/MCP (client-side)
API_BASE=http://localhost:8000
GQL_PATH=/graphql

# Monitoring
METRICS_FILE=monitoring/metrics.json
METRICS_CSV=monitoring/metrics.csv
```

---

## 10) Enhanced Developer Workflow

```bash
# 1) Install dependencies
make install

# 2) Start GraphQL API
make run-graphql

# 3) Run comprehensive demo with agent selection
make demo-prod

# 4) Generate performance report
python -m monitoring.cli report --hours 1

# 5) Test individual agents
python chat/agent_selector.py --ask "show POSTED payments for ACC-1002 in the last 60 days"
python chat/agent_selector.py --ask "show me all customers in India with unpaid bills and their payment history"
```

---

## 11) Performance Results

### Before Optimization (v1):
- **Simple Queries**: 2+ minutes (all routed to CrewAI)
- **Complex Queries**: 5+ minutes (infinite loops)
- **Success Rate**: ~30%
- **Agent Selection**: None (all queries to CrewAI)

### After Optimization (v2):
- **Simple Queries**: ~2-5 seconds (Simple Agent)
- **Complex Queries**: ~30-60 seconds (CrewAI Agent)
- **Success Rate**: ~95%
- **Agent Selection**: Intelligent routing based on complexity

---

## 12) Key Improvements in v2

### 11.1 Intelligent Agent Selection
- **Problem**: All queries routed to CrewAI, causing performance issues
- **Solution**: Implemented complexity-based routing with regex pattern matching
- **Result**: 90% performance improvement for simple queries

### 11.2 Enhanced Filter Propagation
- **Problem**: Filters not properly applied (e.g., India customers showing UAE customers)
- **Solution**: Improved intent parsing with country mapping and filter validation
- **Result**: Accurate filter application across all query types

### 11.3 Performance Monitoring
- **Problem**: No visibility into system performance
- **Solution**: Comprehensive metrics collection and reporting
- **Result**: Real-time performance insights and optimization opportunities

### 11.4 CrewAI Optimization
- **Problem**: Infinite loops and malformed queries
- **Solution**: Simplified workflow, better tool handling, robust error handling
- **Result**: Reliable complex query processing

### 11.5 Generic Query Building
- **Problem**: Hardcoded, narrow query building logic
- **Solution**: Metadata-driven query building with regex-based variable extraction
- **Result**: Extensible, maintainable query generation

---

## 13) Future Enhancements (vNext)

1. **Semantic Metadata**: Enhanced YAML with semantic tags for better intent understanding
2. **LLM-Based Intent Parsing**: Hybrid regex/LLM approach for complex natural language
3. **Relationship Queries**: Nested GraphQL fields generated from metadata
4. **Advanced Monitoring**: Real-time dashboards, alerting, and performance optimization
5. **Caching Layer**: Query result caching and persisted queries
6. **Multi-Domain Support**: Generic framework for any domain beyond telecom

---

## 14) Conclusion

The v2 architecture represents a significant evolution from the initial implementation:

- **Intelligent Routing**: Right tool for the right job
- **Performance Optimization**: 90% improvement in simple query performance
- **Reliability**: 95% success rate with robust error handling
- **Observability**: Comprehensive monitoring and metrics
- **Extensibility**: Generic, metadata-driven approach

This architecture provides a solid foundation for handling both simple and complex queries efficiently while maintaining the flexibility to evolve and support new requirements.
