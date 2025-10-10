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
    # allow healthz without key
    if request.url.path == "/healthz":
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
# Mount the DYNAMIC GraphQL schema at /graphql
# --------------------------------------------------------------------------------------
# IMPORTANT: This must come AFTER middlewares are defined so requests pass through them.
app.include_router(build_dynamic_router(path="/graphql"))
