# --- Makefile (add/replace these bits) ---
SHELL := /bin/bash

# Point to your .env; override with `make ENV_FILE=path/to/.env <target>`
ENV_FILE ?= .env

# Load .env keys as Make variables (safe if file missing)
export $(shell sed -n 's/^\([A-Za-z_][A-Za-z0-9_]*\)=.*/\1/p' $(ENV_FILE) 2>/dev/null)

API_BASE ?= http://localhost:8000
GQL_PATH ?= /graphql
# API_KEY is used by the server; TELECOM_API_KEY used by client (mcp_call/agent)
API_KEY  ?= dev-key
MODEL    ?= llama3.1

MCP_SERVER ?= mcp_server/server.py
AGENT      ?= chat/agent.py
MCP_CALL   ?= mcp_call.py

.PHONY: help install run-graphql health mcp-call demo demo-mock demo-prod print-env

help:
	@echo "make install      # install deps (incl. mcp)"
	@echo "make run-graphql  # start GraphQL API on :8080 (loads .env)"
	@echo "make health       # GET /healthz"
	@echo "make mcp-call     # one-off MCP call"
	@echo "make demo         # two MCP agent prompts (production MCP)"
	@echo "make demo-mock    # demo with mock MCP registry"
	@echo "make demo-prod    # demo with production MCP server"
	@echo "make print-env    # show effective env vars"

install:
	set -a; [ -f $(ENV_FILE) ] && . $(ENV_FILE); set +a; \
	python -m pip install -U pip && \
	( test -f requirements.txt && python -m pip install -r requirements.txt || true ); \
	python -m pip install -U "mcp>=0.4.0" anyio httpx python-dotenv ollama

run-graphql:
	set -a; [ -f $(ENV_FILE) ] && . $(ENV_FILE); set +a; \
	uvicorn app.main:app --host 0.0.0.0 --port 8000

health:
	curl -s $(API_BASE)/healthz | jq . || curl -s $(API_BASE)/healthz

mcp-call:
	set -a; [ -f $(ENV_FILE) ] && . $(ENV_FILE); set +a; \
	: $${API_KEY:?Please set API_KEY in $(ENV_FILE)}; \
	TELECOM_API_BASE=$(API_BASE) TELECOM_GQL_PATH=$(GQL_PATH) TELECOM_API_KEY=$${TELECOM_API_KEY:-$${API_KEY}} \
	python $(MCP_CALL)

print-env:
	set -a; [ -f $(ENV_FILE) ] && . $(ENV_FILE); set +a; \
	echo "ENV_FILE=$(ENV_FILE)"; \
	echo "API_BASE=$(API_BASE)"; \
	echo "GQL_PATH=$(GQL_PATH)"; \
	echo "API_KEY=$${API_KEY:-<unset in shell>}"; \
	echo "TELECOM_API_KEY=$${TELECOM_API_KEY:-<unset in shell>}"; \
	echo "CATALOG=$${CATALOG:-<unset>}"; \
	echo "SCHEMA=$${SCHEMA:-<unset>}"; \
	echo "DATABRICKS_HOST=$${DATABRICKS_HOST:-<unset>}"

demo: demo-prod

demo-prod:
	@echo "🚀 Production MCP Demo - Using real MCP server for AI agent communication"
	@echo ""
	@echo "📋 Prerequisites:"
	@echo "   • GraphQL server must be running on $(API_BASE)"
	@echo "   • Start it with: make run-graphql"
	@echo "   • Or manually: uvicorn app.main:app --host 0.0.0.0 --port 8000"
	@echo ""
	@echo "🔧 Environment:"
	@echo "   • API Base: $(API_BASE)"
	@echo "   • GraphQL Path: $(GQL_PATH)"
	@echo "   • MCP Server: $(MCP_SERVER)"
	@echo ""
	@echo "🧪 Running demo queries..."
	@echo "============================================================"
	set -a; [ -f $(ENV_FILE) ] && . $(ENV_FILE); set +a; \
	: $${API_KEY:?Please set API_KEY in $(ENV_FILE)}; \
	export TELECOM_API_BASE=$(API_BASE); \
	export TELECOM_GQL_PATH=$(GQL_PATH); \
	export TELECOM_API_KEY=$${TELECOM_API_KEY:-$${API_KEY}}; \
	echo ">> Query 1: payments last 60 days (Agent Selector)"; \
	python chat/agent_selector.py \
		--ask "show POSTED payments for ACC-1002 in the last 60 days"; \
	echo ""; \
	echo ">> Query 2: bill + payments (Agent Selector)"; \
	python chat/agent_selector.py \
		--ask "get bill BILL-9001 and list its payments"; \
	echo ""; \
	echo ">> Query 3: complex multi-entity query (Agent Selector)"; \
	python chat/agent_selector.py \
		--ask "show me all customers in India with unpaid bills and their payment history"; \
	echo ""; \
	echo "📊 Generating Performance Metrics Report..."; \
	python -m monitoring.cli report --hours 1; \
	echo ""; \
	echo "✅ Demo completed successfully!"

demo-mock:
	@echo "🧪 Mock MCP Demo - Using mock registry for contract registration"
	set -a; [ -f $(ENV_FILE) ] && . $(ENV_FILE); set +a; \
	: $${API_KEY:?Please set API_KEY in $(ENV_FILE)}; \
	export TELECOM_API_BASE=$(API_BASE); \
	export TELECOM_GQL_PATH=$(GQL_PATH); \
	export TELECOM_API_KEY=$${TELECOM_API_KEY:-$${API_KEY}}; \
	export MCP_URL=http://127.0.0.1:9000/register; \
	echo "Starting mock MCP registry..."; \
	python scripts/mock_mcp.py & \
	sleep 2; \
	echo "Registering contracts with mock MCP..."; \
	make register; \
	echo "Running agent demo with production MCP server..."; \
	python chat/agent.py --server $(MCP_SERVER) \
		--ask "show POSTED payments for ACC-1002 in the last 30 days"; \
	echo ""; \
	python chat/agent.py --server $(MCP_SERVER) \
		--ask "get bill BILL-9001 and list its payments"; \
	pkill -f "mock_mcp.py" || true

# === Auto contract + registration workflow ===
.PHONY: regen export register all

regen:
	python scripts/gen_registry_from_spec.py dp/telecom.yml registry/ --verbose
	python -m app.runtime.schema_generator registry > /dev/null

export:
	python scripts/export_contracts.py

register:
	python scripts/mcp_register_from_contracts.py --retries 3

all: regen export register		