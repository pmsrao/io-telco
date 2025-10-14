import os
import argparse
import httpx
from dotenv import load_dotenv

# MCP SDK
from mcp.server.fastmcp import FastMCP

load_dotenv()

API_BASE = os.getenv("TELECOM_API_BASE", "http://localhost:8080")
GQL_PATH = os.getenv("TELECOM_GQL_PATH", "/graphql")  # or /graphql-meta if MODE=both
API_KEY  = os.getenv("TELECOM_API_KEY", "dev-key")
RES_BASE = os.getenv("TELECOM_RES_BASE", API_BASE)

app = FastMCP("telecom")

import os, json, time, logging
from uuid import uuid4
import httpx

LOG = logging.getLogger("telecom.mcp")
LOG.setLevel(logging.INFO)
_sh = logging.StreamHandler()
_sh.setFormatter(logging.Formatter("%(message)s"))
LOG.addHandler(_sh)

API_BASE = os.environ.get("TELECOM_API_BASE", "http://localhost:8080")
GQL_PATH = os.environ.get("TELECOM_GQL_PATH", "/graphql")
API_KEY  = os.environ.get("TELECOM_API_KEY", "dev-key")

# ----------------- Discovery Tools -----------------
@app.tool("telecom.discover.products")
def discover_products() -> str:
    """Discover available data products and their contracts"""
    cid = str(uuid4())
    t0 = time.time()
    url = f"{RES_BASE}/.well-known/telecom.registry.index"
    
    try:
        r = httpx.get(url, timeout=30.0)
        r.raise_for_status()
        result = r.json()
        
        LOG.info(json.dumps({
            "cid": cid,
            "tool": "telecom.discover.products",
            "status": r.status_code,
            "dur_ms": int((time.time()-t0)*1000),
            "products_found": len(result.get("data_products", [])),
        }))
        
        return json.dumps(result)
    except Exception as e:
        LOG.error(json.dumps({
            "cid": cid, "tool": "telecom.discover.products",
            "error": str(e),
        }))
        return json.dumps({"error": str(e), "cid": cid})

@app.tool("telecom.get.contract")
def get_contract(product: str) -> str:
    """Get contract details for a specific data product"""
    cid = str(uuid4())
    t0 = time.time()
    url = f"{RES_BASE}/.well-known/telecom.registry/{product}.yaml"
    
    try:
        r = httpx.get(url, timeout=30.0)
        r.raise_for_status()
        result = r.json()
        
        LOG.info(json.dumps({
            "cid": cid,
            "tool": "telecom.get.contract",
            "product": product,
            "status": r.status_code,
            "dur_ms": int((time.time()-t0)*1000),
            "entities": len(result.get("entities", {})),
        }))
        
        return json.dumps(result)
    except Exception as e:
        LOG.error(json.dumps({
            "cid": cid, "tool": "telecom.get.contract",
            "product": product,
            "error": str(e),
        }))
        return json.dumps({"error": str(e), "cid": cid})

@app.tool("telecom.schema.introspect")
def schema_introspect() -> str:
    """Get the complete GraphQL schema for all data products"""
    cid = str(uuid4())
    t0 = time.time()
    url = f"{RES_BASE}/.well-known/telecom.graphql.sdl"
    
    try:
        r = httpx.get(url, timeout=30.0)
        r.raise_for_status()
        sdl = r.text
        
        LOG.info(json.dumps({
            "cid": cid,
            "tool": "telecom.schema.introspect",
            "status": r.status_code,
            "dur_ms": int((time.time()-t0)*1000),
            "sdl_length": len(sdl),
        }))
        
        return sdl
    except Exception as e:
        LOG.error(json.dumps({
            "cid": cid, "tool": "telecom.schema.introspect",
            "error": str(e),
        }))
        return json.dumps({"error": str(e), "cid": cid})

# ----------------- Tool: run GraphQL -----------------
@app.tool("telecom.graphql.run")
def graphql_run(query: str, variables: dict | None = None) -> str:
    cid = str(uuid4())
    t0 = time.time()
    url = f"{API_BASE}{GQL_PATH}"
    payload = {"query": query, "variables": variables or {}}
    headers = {"x-api-key": API_KEY, "x-correlation-id": cid, "Content-Type": "application/json"}

    try:
        r = httpx.post(url, headers=headers, json=payload, timeout=60.0)
        txt = r.text
        LOG.info(json.dumps({
            "cid": cid,
            "tool": "telecom.graphql.run",
            "status": r.status_code,
            "dur_ms": int((time.time()-t0)*1000),
            "bytes": len(txt),
        }))
        r.raise_for_status()
        return txt  # text so clients can json.loads(...)
    except Exception as e:
        LOG.error(json.dumps({
            "cid": cid, "tool": "telecom.graphql.run",
            "error": str(e),
        }))
        # surface error to client as JSON text
        return json.dumps({"error": str(e), "cid": cid})


# ----------------- Resources: SDL + Registry -----------------
@app.resource("resource://telecom/graphql-sdl")
def graphql_sdl() -> str:
    r = httpx.get(f"{RES_BASE}/.well-known/telecom.graphql.sdl", timeout=30.0)
    r.raise_for_status()
    return r.text

@app.resource("resource://telecom/registry-index")
def registry_index() -> str:
    r = httpx.get(f"{RES_BASE}/.well-known/telecom.registry.index", timeout=30.0)
    r.raise_for_status()
    return r.text

@app.resource("resource://telecom/registry/customer.yaml")
def registry_customer() -> str:
    r = httpx.get(f"{RES_BASE}/.well-known/telecom.registry/customer.yaml", timeout=30.0)
    r.raise_for_status()
    return r.text

@app.resource("resource://telecom/registry/payments.yaml")
def registry_payments() -> str:
    r = httpx.get(f"{RES_BASE}/.well-known/telecom.registry/payments.yaml", timeout=30.0)
    r.raise_for_status()
    return r.text

# ----------------- Entrypoint -----------------
if __name__ == "__main__":
    import sys
    ap = argparse.ArgumentParser()
    ap.add_argument("--tcp", type=int, default=0, help="Run in TCP mode on this port; falls back to stdio if unsupported")
    args = ap.parse_args()

    # Prefer TCP if requested AND supported by this SDK
    if args.tcp and hasattr(app, "run_tcp"):
        app.run_tcp("127.0.0.1", args.tcp)
    else:
        if args.tcp and not hasattr(app, "run_tcp"):
            print("[telecom-mcp] TCP mode not supported by this MCP SDK; falling back to stdio.", file=sys.stderr)
        # stdio mode (works across SDK versions)
        if hasattr(app, "run"):
            app.run()
        else:
            # extremely old SDKs might use a different entrypoint; last-resort import
            try:
                from mcp.server.fastmcp import run as run_stdio
                run_stdio(app)
            except Exception as e:
                print(f"[telecom-mcp] Could not start in stdio mode: {e}", file=sys.stderr)
                sys.exit(1)

