#!/usr/bin/env python3
import os, sys, yaml, json
from typing import Dict, Any, List, Iterable, Tuple

VERBOSE = "--verbose" in sys.argv
ONLY_DP = None

def vprint(*args, **kwargs):
    if VERBOSE: print(*args, **kwargs)

def read_yaml(path: str) -> Dict[str, Any]:
    with open(path, "r") as f: return yaml.safe_load(f)

def write_yaml(path: str, data: Dict[str, Any]):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f: yaml.safe_dump(data, f, sort_keys=False)

SCALAR_MAP = {
    "STRING": "String", "VARCHAR": "String", "CHAR": "String", "TEXT": "String",
    "INT": "Int", "INTEGER": "Int", "BIGINT": "Int", "SMALLINT": "Int",
    "FLOAT": "Float", "REAL": "Float",
    "DOUBLE": "Decimal", "DECIMAL": "Decimal", "NUMERIC": "Decimal",
    "BOOLEAN": "Boolean", "DATE": "Timestamp", "TIMESTAMP": "Timestamp",
}

def map_dtype(dtype: str) -> str:
    return SCALAR_MAP.get(str(dtype or "STRING").upper().split("(")[0], "String")

def _iter_data_products(spec: Dict[str, Any]) -> Iterable[Tuple[str, Dict[str, Any]]]:
    for k in ("data_products","dataProducts","products"):
        arr = spec.get(k)
        if isinstance(arr, list):
            for dp in arr:
                name = dp.get("name") or dp.get("product") or dp.get("id") or "default"
                yield name, dp
            return
    if "entities" in spec:
        yield spec.get("name","default"), {"entities": spec["entities"]}; return
    raise SystemExit("Spec missing products/data_products/entities")

def _normalize_columns(ent: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    cols = ent.get("columns")
    if isinstance(cols, dict):
        return {k: {"scalar": map_dtype(v.get("type") if isinstance(v, dict) else v)} for k, v in cols.items()}
    if isinstance(cols, list):
        out = {}
        for c in cols:
            if isinstance(c, dict) and c.get("name"):
                out[c["name"]] = {"scalar": map_dtype(c.get("type"))}
        return out
    return {}

def _normalize_filters(filters: Any) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for f in (filters or []):
        if not isinstance(f, dict): continue
        name = f.get("name")
        if not name: continue
        out.append({
            "name": name,
            "type": f.get("type"),
            "op": f.get("op") or f.get("operator"),
            "column": f.get("column") or name,
            **({"columns": f["columns"]} if "columns" in f else {}),
        })
    return out

def _collect_aliases(dp: Dict[str, Any]) -> Dict[str, List[str]]:
    aliases = {}
    for q in (dp.get("expose",{}) or {}).get("queries",[]) or []:
        if isinstance(q, dict):
            qname, qspec = next(iter(q.items()))
            if isinstance(qspec, dict) and qspec.get("entity"):
                aliases.setdefault(qspec["entity"], []).append(qname)
    return aliases

def generate_registry(spec_path: str, out_dir: str):
    spec = read_yaml(spec_path)
    os.makedirs(out_dir, exist_ok=True)
    per_dp: Dict[str, Dict[str, Any]] = {}
    for dp_name, dp in _iter_data_products(spec):
        entities = dp.get("entities") or []
        if isinstance(entities, dict):
            entities = [{"logical_name": k, **(v or {})} for k, v in entities.items()]
        vprint(f"[dp] {dp_name}: {len(entities)} entities")
        alias_map = _collect_aliases(dp)
        for e in entities:
            name = e.get("logical_name") or e.get("name")
            if not name:
                vprint(f"[warn] unnamed entity in dp={dp_name} → skipped"); continue
            catalog = os.environ.get("CATALOG") or "${CATALOG}"
            schema  = os.environ.get("SCHEMA") or "${SCHEMA}"
            table   = e.get("table") or f"{catalog}.{schema}.{name}"
            columns = _normalize_columns(e)
            filters = _normalize_filters(e.get("filters"))
            # carry per-query extras from expose.queries if present
            order_by_default = None
            default_limit = 200; max_limit = 2000; required_window = False
            for q in (dp.get("expose",{}) or {}).get("queries",[]) or []:
                if isinstance(q, dict):
                    qname, qspec = next(iter(q.items()))
                    if isinstance(qspec, dict) and qspec.get("entity") == name:
                        order_by_default = qspec.get("order_by_default", order_by_default)
                        pag = qspec.get("pagination") or {}
                        default_limit = pag.get("default_limit", default_limit)
                        max_limit = pag.get("max_limit", max_limit)
                        required_window = qspec.get("required_window", required_window)

            per_dp.setdefault(dp_name, {"data_product": dp_name, "entities": {}})
            per_dp[dp_name]["entities"][name] = {
                "table": table,
                "key": e.get("primary_key") or e.get("key"),
                "columns": columns,
                "filters": filters,
                "aliases": alias_map.get(name, []),
                "order_by_default": order_by_default,
                "pagination": {"default_limit": default_limit, "max_limit": max_limit},
                "policy": {"required_window": required_window},
            }

    written = 0
    for dp_name, doc in per_dp.items():
        out_path = os.path.join(out_dir, f"{dp_name}.yaml")
        write_yaml(out_path, doc)
        ents = doc.get("entities") or {}
        total_cols = sum(len(v.get("columns") or {}) for v in ents.values())
        vprint(f"[ok] wrote {out_path} ({len(ents)} entities, {total_cols} total columns)")
        written += 1
    print(f"✅ Done. Generated/updated {written} file(s) in {out_dir}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scripts/gen_registry_from_spec.py <spec.yml> <out_dir> [--verbose]")
        sys.exit(1)
    if "--only" in sys.argv:
        try:
            ONLY_DP = sys.argv[sys.argv.index("--only")+1]
        except Exception:
            print("Error: --only requires value"); sys.exit(1)
    generate_registry(sys.argv[1], sys.argv[2])