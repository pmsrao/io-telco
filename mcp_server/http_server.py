#!/usr/bin/env python3
"""
HTTP-based MCP Server for Telecom Data Products
This version runs as a standalone HTTP server, allowing us to see logs in real-time
"""

import os
import json
import time
import logging
import asyncio
from uuid import uuid4
from typing import Dict, Any, List
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# Configure logging
LOG = logging.getLogger("telecom.mcp.http")
LOG.setLevel(logging.INFO)
_sh = logging.StreamHandler()
_sh.setFormatter(logging.Formatter("%(asctime)s - MCP-HTTP - %(message)s"))
LOG.addHandler(_sh)

# Environment variables
API_BASE = os.environ.get("TELECOM_API_BASE", "http://localhost:8000")
GQL_PATH = os.environ.get("TELECOM_GQL_PATH", "/graphql")
API_KEY = os.environ.get("TELECOM_API_KEY", "dev-key")
RES_BASE = os.environ.get("TELECOM_RES_BASE", API_BASE)

# FastAPI app
app = FastAPI(title="Telecom MCP HTTP Server", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response models
class ToolRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = {}

class ToolResponse(BaseModel):
    success: bool
    result: Any = None
    error: str = None
    duration_ms: int = 0

# ----------------- Discovery Tools -----------------
async def discover_products() -> str:
    """Discover available data products and their contracts"""
    cid = str(uuid4())
    t0 = time.time()
    url = f"{RES_BASE}/.well-known/telecom.registry.index"
    
    LOG.info(f"🔧 TOOL INVOKED: telecom.discover.products")
    LOG.info(f"📡 Request URL: {url}")
    
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(url, timeout=30.0)
            r.raise_for_status()
            result = r.json()
        
        dur_ms = int((time.time()-t0)*1000)
        products_count = len(result.get("data_products", []))
        LOG.info(f"✅ Discovered {products_count} data products ({dur_ms}ms)")
        
        return json.dumps(result)
    except Exception as e:
        dur_ms = int((time.time()-t0)*1000)
        LOG.error(f"❌ Failed to discover products ({dur_ms}ms): {e}")
        return json.dumps({"error": str(e)})

async def get_contract(product: str) -> str:
    """Get contract details for a specific data product"""
    cid = str(uuid4())
    t0 = time.time()
    url = f"{RES_BASE}/.well-known/telecom.registry/{product}.yaml"
    
    LOG.info(f"🔧 TOOL INVOKED: telecom.contract.get")
    LOG.info(f"📦 Product: {product}")
    LOG.info(f"📡 Request URL: {url}")
    
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(url, timeout=30.0)
            r.raise_for_status()
            result = r.json()
        
        dur_ms = int((time.time()-t0)*1000)
        LOG.info(f"✅ Retrieved contract for {product} ({dur_ms}ms)")
        
        return json.dumps(result)
    except Exception as e:
        dur_ms = int((time.time()-t0)*1000)
        LOG.error(f"❌ Failed to get contract for {product} ({dur_ms}ms): {e}")
        return json.dumps({"error": str(e)})

async def get_schema() -> str:
    """Get the GraphQL schema"""
    cid = str(uuid4())
    t0 = time.time()
    url = f"{API_BASE}{GQL_PATH}"
    
    LOG.info(f"🔧 TOOL INVOKED: telecom.schema.get")
    LOG.info(f"📡 Request URL: {url}")
    
    try:
        # GraphQL introspection query
        introspection_query = {
            "query": """
            query IntrospectionQuery {
                __schema {
                    queryType { name }
                    mutationType { name }
                    subscriptionType { name }
                    types {
                        ...FullType
                    }
                    directives {
                        name
                        description
                        locations
                        args {
                            ...InputValue
                        }
                    }
                }
            }
            fragment FullType on __Type {
                kind
                name
                description
                fields(includeDeprecated: true) {
                    name
                    description
                    args {
                        ...InputValue
                    }
                    type {
                        ...TypeRef
                    }
                    isDeprecated
                    deprecationReason
                }
                inputFields {
                    ...InputValue
                }
                interfaces {
                    ...TypeRef
                }
                enumValues(includeDeprecated: true) {
                    name
                    description
                    isDeprecated
                    deprecationReason
                }
                possibleTypes {
                    ...TypeRef
                }
            }
            fragment InputValue on __InputValue {
                name
                description
                type { ...TypeRef }
                defaultValue
            }
            fragment TypeRef on __Type {
                kind
                name
                ofType {
                    kind
                    name
                    ofType {
                        kind
                        name
                        ofType {
                            kind
                            name
                            ofType {
                                kind
                                name
                                ofType {
                                    kind
                                    name
                                    ofType {
                                        kind
                                        name
                                        ofType {
                                            kind
                                            name
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
            """
        }
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": API_KEY
        }
        
        async with httpx.AsyncClient() as client:
            r = await client.post(url, json=introspection_query, headers=headers, timeout=30.0)
            r.raise_for_status()
            result = r.json()
        
        dur_ms = int((time.time()-t0)*1000)
        LOG.info(f"✅ Retrieved GraphQL schema ({dur_ms}ms)")
        
        return json.dumps(result)
    except Exception as e:
        dur_ms = int((time.time()-t0)*1000)
        LOG.error(f"❌ Failed to get schema ({dur_ms}ms): {e}")
        return json.dumps({"error": str(e)})

async def run_graphql_query(query: str, variables: Dict[str, Any] = None) -> str:
    """Execute a GraphQL query against the telecom API"""
    cid = str(uuid4())
    t0 = time.time()
    url = f"{API_BASE}{GQL_PATH}"
    
    LOG.info(f"🔧 TOOL INVOKED: telecom.graphql.run")
    LOG.info(f"📝 GraphQL Query: {query}")
    LOG.info(f"📝 Variables: {json.dumps(variables or {}, indent=2)}")
    LOG.info(f"📡 Request URL: {url}")
    
    try:
        payload = {
            "query": query,
            "variables": variables or {}
        }
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": API_KEY
        }
        
        async with httpx.AsyncClient() as client:
            r = await client.post(url, json=payload, headers=headers, timeout=30.0)
            r.raise_for_status()
            result = r.json()
        
        dur_ms = int((time.time()-t0)*1000)
        response_size = len(json.dumps(result))
        LOG.info(f"✅ GraphQL executed successfully ({dur_ms}ms)")
        LOG.info(f"📊 Response size: {response_size} bytes")
        
        return json.dumps(result)
    except Exception as e:
        dur_ms = int((time.time()-t0)*1000)
        LOG.error(f"❌ GraphQL execution failed ({dur_ms}ms): {e}")
        return json.dumps({"error": str(e)})

# ----------------- API Endpoints -----------------
@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Telecom MCP HTTP Server is running", "version": "1.0.0"}

@app.get("/tools")
async def list_tools():
    """List available tools"""
    tools = [
        {
            "name": "telecom.discover.products",
            "description": "Discover available data products and their contracts",
            "parameters": {}
        },
        {
            "name": "telecom.contract.get",
            "description": "Get contract details for a specific data product",
            "parameters": {"product": {"type": "string", "description": "Data product name"}}
        },
        {
            "name": "telecom.schema.get",
            "description": "Get the GraphQL schema",
            "parameters": {}
        },
        {
            "name": "telecom.graphql.run",
            "description": "Execute a GraphQL query against the telecom API",
            "parameters": {
                "query": {"type": "string", "description": "GraphQL query"},
                "variables": {"type": "object", "description": "Query variables"}
            }
        }
    ]
    return {"tools": tools}

@app.post("/tools/execute", response_model=ToolResponse)
async def execute_tool(request: ToolRequest):
    """Execute a tool with given arguments"""
    t0 = time.time()
    
    LOG.info(f"🚀 EXECUTING TOOL: {request.tool_name}")
    LOG.info(f"📋 Arguments: {json.dumps(request.arguments, indent=2)}")
    
    try:
        if request.tool_name == "telecom.discover.products":
            result = await discover_products()
        elif request.tool_name == "telecom.contract.get":
            product = request.arguments.get("product", "")
            result = await get_contract(product)
        elif request.tool_name == "telecom.schema.get":
            result = await get_schema()
        elif request.tool_name == "telecom.graphql.run":
            query = request.arguments.get("query", "")
            variables = request.arguments.get("variables", {})
            result = await run_graphql_query(query, variables)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown tool: {request.tool_name}")
        
        dur_ms = int((time.time()-t0)*1000)
        LOG.info(f"✅ TOOL COMPLETED: {request.tool_name} ({dur_ms}ms)")
        
        return ToolResponse(
            success=True,
            result=result,
            duration_ms=dur_ms
        )
        
    except Exception as e:
        dur_ms = int((time.time()-t0)*1000)
        LOG.error(f"❌ TOOL FAILED: {request.tool_name} ({dur_ms}ms): {e}")
        
        return ToolResponse(
            success=False,
            error=str(e),
            duration_ms=dur_ms
        )

if __name__ == "__main__":
    import uvicorn
    
    LOG.info("🌐 Starting Telecom MCP HTTP Server...")
    LOG.info(f"🔧 API Base: {API_BASE}")
    LOG.info(f"🔧 GraphQL Path: {GQL_PATH}")
    LOG.info(f"🔧 Registry Base: {RES_BASE}")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        log_level="info"
    )
