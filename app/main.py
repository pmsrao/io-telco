# app/main.py
from __future__ import annotations

import os
from dotenv import load_dotenv

# Load .env (default) or a custom file via ENV_FILE
load_dotenv(dotenv_path=os.getenv("ENV_FILE", ".env"), override=False)

import json
import time
import logging
import re
from uuid import uuid4

from fastapi import FastAPI, Request, HTTPException
from starlette.responses import Response, JSONResponse

# 🚩 DYNAMIC GraphQL schema/router
from .meta_graphql import build_dynamic_router


# --------------------------------------------------------------------------------------
# App + Config
# --------------------------------------------------------------------------------------

API_KEY = os.getenv("API_KEY", "dev-key")

app = FastAPI(title="Telecom GraphQL (Dynamic)")

# --------------------------------------------------------------------------------------
# API-key guard (x-api-key)
# --------------------------------------------------------------------------------------
@app.middleware("http")
async def api_key_guard(request: Request, call_next):
    # allow healthz and well-known endpoints without key
    if request.url.path in ["/healthz"] or request.url.path.startswith("/.well-known/"):
        return await call_next(request)

    key = request.headers.get("x-api-key")
    if key != API_KEY:
        return JSONResponse({"detail": "Invalid or missing x-api-key"}, status_code=401)

    return await call_next(request)

# --------------------------------------------------------------------------------------
# Observability middleware (correlation id + PII redaction)
# --------------------------------------------------------------------------------------

LOG = logging.getLogger("telecom.graphql")
LOG.setLevel(logging.INFO)
_handler = logging.StreamHandler()
_handler.setFormatter(logging.Formatter("%(message)s"))
LOG.addHandler(_handler)

EMAIL_RE = re.compile(r'([A-Za-z0-9._%+-])([A-Za-z0-9._%+-]*)(@[A-Za-z0-9.-]+\.[A-Za-z]{2,})')
PHONE_RE = re.compile(r'(\+?\d{2,3})[-\s.]?(\d{3})[-\s.]?(\d{3,4})[-\s.]?(\d{3,4})')

def _redact(s: str) -> str:
    if not s:
        return s
    s = EMAIL_RE.sub(lambda m: f"{m.group(1)}***{m.group(3)}", s)
    s = PHONE_RE.sub(lambda m: f"{m.group(1)}-***-***-{m.group(4)}", s)
    return s

@app.middleware("http")
async def observability(request: Request, call_next):
    cid = request.headers.get("x-correlation-id") or str(uuid4())
    started = time.time()

    # capture small bodies (GraphQL posts)
    try:
        raw = await request.body()
        body_txt = raw.decode("utf-8")[:4000]
    except Exception:
        body_txt = ""

    safe_body = _redact(body_txt)

    response: Response
    try:
        response = await call_next(request)
    finally:
        dur_ms = int((time.time() - started) * 1000)
        LOG.info(json.dumps({
            "ts": time.time(),
            "cid": cid,
            "method": request.method,
            "path": request.url.path,
            "status": getattr(response, "status_code", 0),
            "dur_ms": dur_ms,
            "body": safe_body,
        }))
    response.headers["x-correlation-id"] = cid
    return response

# --------------------------------------------------------------------------------------
# Health
# --------------------------------------------------------------------------------------
@app.get("/healthz")
def healthz():
    return {"ok": True, "mode": "dynamic"}

# --------------------------------------------------------------------------------------
# Well-Known Endpoints for MCP Discovery
# --------------------------------------------------------------------------------------
@app.get("/.well-known/telecom.graphql.sdl")
def get_graphql_sdl():
    """Return the GraphQL Schema Definition Language"""
    from app.runtime.registry_loader import Registry
    from app.runtime.schema_generator import SchemaGenerator
    
    registry = Registry(root="registry")
    sg = SchemaGenerator()
    sdl = sg.stitch(registry)
    return sdl

@app.get("/.well-known/telecom.registry.index")
def get_registry_index():
    """Return index of available data products and their contracts"""
    import os
    import yaml
    
    index = {
        "data_products": [],
        "contracts": {},
        "endpoints": {
            "graphql": "/graphql",
            "health": "/healthz"
        }
    }
    
    # Scan registry directory for data products
    registry_dir = "registry"
    if os.path.exists(registry_dir):
        for file in os.listdir(registry_dir):
            if file.endswith('.yaml') and file != '_settings.yaml':
                product_name = file.replace('.yaml', '')
                index["data_products"].append(product_name)
                
                # Load contract details
                try:
                    with open(os.path.join(registry_dir, file), 'r') as f:
                        contract = yaml.safe_load(f)
                        index["contracts"][product_name] = {
                            "entities": list(contract.get("entities", {}).keys()),
                            "aliases": []
                        }
                        # Extract aliases from entities
                        for entity_name, entity_data in contract.get("entities", {}).items():
                            aliases = entity_data.get("aliases", [])
                            index["contracts"][product_name]["aliases"].extend(aliases)
                except Exception as e:
                    LOG.warning(f"Failed to load contract for {product_name}: {e}")
    
    return index

@app.get("/.well-known/telecom.registry/{product}.yaml")
def get_registry_product(product: str):
    """Return registry YAML for a specific data product"""
    import os
    import yaml
    
    registry_file = f"registry/{product}.yaml"
    if not os.path.exists(registry_file):
        raise HTTPException(status_code=404, detail=f"Data product '{product}' not found")
    
    with open(registry_file, 'r') as f:
        return yaml.safe_load(f)

# --------------------------------------------------------------------------------------
# Mount the DYNAMIC GraphQL schema at /graphql
# --------------------------------------------------------------------------------------
# IMPORTANT: This must come AFTER middlewares are defined so requests pass through them.
app.include_router(build_dynamic_router(path="/graphql"))
