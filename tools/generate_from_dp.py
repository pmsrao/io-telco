#!/usr/bin/env python3
import argparse, os, re, sys, yaml
from pathlib import Path
from typing import Dict, Any, List

TYPE_MAP = {
    "STRING": "STRING",
    "INT": "INT",
    "INTEGER": "INT",
    "BIGINT": "BIGINT",
    "SMALLINT": "SMALLINT",
    "DOUBLE": "DOUBLE",
    "FLOAT": "DOUBLE",
    "BOOLEAN": "BOOLEAN",
    "DATE": "DATE",
    "TIMESTAMP": "TIMESTAMP",
}

def db_type(t: str) -> str:
    t = t.strip().upper()
    if re.match(r"DECIMAL\(\d+,\s*\d+\)", t):
        return t
    return TYPE_MAP.get(t, "STRING")

def load_master(path: Path) -> Dict[str, Any]:
    return yaml.safe_load(path.read_text())

def ensure_dirs(*paths: Path):
    for p in paths:
        p.mkdir(parents=True, exist_ok=True)

def phys_name(logical: str, version: str) -> str:
    v = version.lstrip("v")
    return f"{logical}_v{v}"

def make_registry_product(prod: Dict[str, Any], catalog: str, schema: str) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "product": prod["product"],
        "version": prod.get("version", "v1"),
        "namespace": f"{catalog}.{schema}",
        "entities": [],
        "relationships": prod.get("relationships", []),
    }
    # Entities
    for e in prod["entities"]:
        logical = e["logical_name"]
        table = e.get("table") or phys_name(logical, out["version"])
        fields = [{"name": c["name"], "type": c["type"]} for c in e["columns"]]
        out["entities"].append({
            "name": logical,
            "table": table,
            "primary_key": e["primary_key"],
            "fields": fields,
        })
    # Expose: copy if present, else generate sensible defaults
    if "expose" in prod:
        out["expose"] = prod["expose"]
    else:
        q = []
        for e in prod["entities"]:
            ln = e["logical_name"]
            pk = e["primary_key"]
            q.append({f"get_{ln}": {"entity": ln, "by_key": pk}})
            # default list_* with q ilike on the first string-like column (if any)
            first_str = next((c["name"] for c in e["columns"] if c["type"].upper() in ("STRING",)), None)
            filters = [{"name": pk, "type": "STRING", "operator": "="}]
            if first_str:
                filters.append({"name": "q", "type": "STRING", "operator": "ILIKE", "column": first_str})
            q.append({f"list_{ln}s": {
                "entity": ln,
                "filters": filters,
                "pagination": {"default_limit": 50, "max_limit": 200},
                "order_by_default": f"-{pk}"
            }})
        out["expose"] = {"queries": q}
    return out

def make_product_ddl(prod: Dict[str, Any], catalog: str, schema: str, version: str) -> str:
    lines = []
    lines.append(f"CREATE CATALOG IF NOT EXISTS {catalog};")
    lines.append(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{schema};")
    lines.append(f"USE {catalog}.{schema};")
    lines.append("")
    for e in prod["entities"]:
        logical = e["logical_name"]
        table = e.get("table") or phys_name(logical, version)
        cols = []
        for c in e["columns"]:
            col_def = f"{c['name']} {db_type(c['type'])}"
            if c.get("nullable") is False:
                col_def += " NOT NULL"
            cols.append(col_def)
        lines.append(f"-- Data Product: {prod['product']} entity {logical}")
        lines.append(f"CREATE TABLE IF NOT EXISTS {table} (")
        lines.append("  " + ",\n  ".join(cols))
        lines.append(") USING DELTA;")
        lines.append("")
    return "\n".join(lines)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--input", required=True, help="Master DP YAML (e.g., dp/telecom.yml)")
    ap.add_argument("--registry-out", default="registry", help="Output dir for registry/*.yaml")
    ap.add_argument("--sql-out", default="generated/sql", help="Output dir for SQL files")
    args = ap.parse_args()

    master = load_master(Path(args.input))
    catalog = master.get("catalog") or os.getenv("CATALOG", "telco")
    schema  = master.get("schema")  or os.getenv("SCHEMA",  "silver")

    reg_dir = Path(args.registry_out)
    sql_dir = Path(args.sql_out)
    ensure_dirs(reg_dir, sql_dir)

    for prod in master["products"]:
        version = prod.get("version", "v1")
        # registry
        reg = make_registry_product(prod, catalog, schema)
        reg_path = reg_dir / f"{prod['product']}.yaml"
        reg_path.write_text(yaml.safe_dump(reg, sort_keys=False))
        # ddl
        ddl = make_product_ddl(prod, catalog, schema, version)
        sql_path = sql_dir / f"{prod['product']}_{version}.sql"
        sql_path.write_text(ddl)

    print(f"✅ Generated registry in {reg_dir} and SQL in {sql_dir}")

if __name__ == "__main__":
    main()
