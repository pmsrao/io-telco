#!/usr/bin/env python3
import os, json, yaml, subprocess, sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from typing import Dict, Any, List
from app.runtime.registry_loader import Registry

SCALARS = """scalar Decimal
scalar Timestamp
scalar JSON

input OrderBy { field: String!, dir: String }

"""

def git_sha():
    try:
        return subprocess.check_output(["git","rev-parse","HEAD"]).decode().strip()
    except Exception:
        return "unknown"

def sdl_entity_type(entity: str, spec: Dict[str, Any]) -> str:
    cols = spec.get("columns") or {}
    lines: List[str] = []
    for col, meta in cols.items():
        scalar = (meta or {}).get("scalar", "String")
        lines.append(f"  {col}: {scalar}")
    body = "\n".join(lines) if lines else "  _empty: String"
    return f"type {entity} {{\n{body}\n}}\n"

def sdl_query_fields_for_entity(entity: str, spec: Dict[str, Any]) -> List[str]:
    fields: List[str] = []
    canonical = f"list_{entity}"
    arglist = "(limit: Int, offset: Int, order_by: [OrderBy!], filter: JSON, where: JSON)"
    fields.append(f"  {canonical}{arglist}: [{entity}!]")
    for alias in (spec.get("aliases") or []):
        if isinstance(alias, str) and alias != canonical and alias.startswith("list_"):
            fields.append(f"  {alias}{arglist}: [{entity}!]")
    return fields

def build_dp_sdl(dp_name: str, entities: Dict[str, Dict[str, Any]]) -> str:
    parts: List[str] = [SCALARS]
    qfields: List[str] = []
    for ent, spec in entities.items():
        parts.append(sdl_entity_type(ent, spec))
        qfields.extend(sdl_query_fields_for_entity(ent, spec))
    parts.append("type Query {\n" + "\n".join(qfields) + "\n}\n")
    return "\n".join(parts)

def build_dp_openapi(dp_name: str, entities: Dict[str, Dict[str, Any]], service_url: str, sha: str) -> Dict[str, Any]:
    ops = []
    for ent, spec in entities.items():
        args = {
            "limit": "Int", "offset": "Int", "order_by": "[OrderBy!]",
            "where": {f["name"]: f.get("type","STRING") for f in (spec.get("filters") or [])}
        }
        ops.append({"name": f"list_{ent}", "kind": "query", "args": args})
        for alias in (spec.get("aliases") or []):
            if isinstance(alias, str) and alias.startswith("list_"):
                ops.append({"name": alias, "kind": "query", "args": args})
    return {
        "openapi": "3.0.3",
        "info": {"title": f"{dp_name.title()} Data Product (GraphQL)", "version": "v1", "x-git-sha": sha},
        "servers": [{"url": service_url}],
        "components": {
            "securitySchemes": {
                "bearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
            }
        },
        "security": [{"bearerAuth": []}],
        "paths": {
            "/graphql": {
                "post": {
                    "summary": "GraphQL endpoint",
                    "operationId": f"{dp_name}_graphql",
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {
                            "type": "object",
                            "properties": {"query": {"type": "string"}, "variables": {"type": "object"}},
                            "required": ["query"]
                        }}}
                    },
                    "responses": {"200": {"description": "GraphQL JSON response", "content": {"application/json": {"schema": {"type": "object"}}}}},
                    "x-graphql-operations": ops
                }
            }
        },
        "x-data-product": {"name": dp_name, "type": "graphql"},
    }

def main():
    contracts = Path("contracts"); contracts.mkdir(exist_ok=True)
    reg = Registry(root="registry")
    service_url = os.getenv("SERVICE_URL", "http://127.0.0.1:8000/graphql")
    sha = git_sha()
    per_dp = {}
    for dp, ent, spec in reg.entities():
        per_dp.setdefault(dp, {})[ent] = spec

    manifest = {"service_url": service_url, "git_sha": sha, "products": []}
    for dp_name, ents in per_dp.items():
        print(f"[contract] generating for {dp_name}")
        sdl = build_dp_sdl(dp_name, ents)
        sdl_path = contracts / f"{dp_name}.graphql"
        sdl_path.write_text(sdl)

        oas = build_dp_openapi(dp_name, ents, service_url, sha)
        oas_path = contracts / f"{dp_name}.openapi.yaml"
        with open(oas_path, "w") as f: yaml.safe_dump(oas, f, sort_keys=False)

        manifest["products"].append({
            "data_product": dp_name,
            "graphql": str(sdl_path),
            "openapi": str(oas_path),
            "entities": sorted(list(ents.keys())),
            "operations": sorted(
                list({f"list_{e}" for e in ents.keys()} |
                     {alias for e in ents.values() for alias in (e.get('aliases') or []) if isinstance(alias, str)})
            )
        })
    (contracts / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"✅ Exported contracts to {contracts}/")
    print(json.dumps(manifest, indent=2))

if __name__ == "__main__":
    main()