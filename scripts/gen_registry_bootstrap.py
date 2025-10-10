#!/usr/bin/env python3
"""
Bootstrap registry YAMLs for both Data Products:
- Customer DP: customer_profile, customer_accounts, customer_subscriptions
- Payments DP: payments (+ bills if present; + adjustments if present)
Reads Databricks creds from .env / environment:
  DATABRICKS_HOST, DATABRICKS_HTTP_PATH, DATABRICKS_TOKEN
Usage:
  python scripts/gen_registry_bootstrap.py --catalog <CAT> --schema <SCH> --out registry
Requires:
  pip install databricks-sql-connector pyyaml python-dotenv
"""

import os, sys, argparse
from pathlib import Path
from typing import Dict, List, Any, Optional

import yaml
from dotenv import load_dotenv
from databricks import sql

# -------------------- helpers --------------------

def connect_databricks():
    host = os.environ.get("DATABRICKS_HOST")
    http_path = os.environ.get("DATABRICKS_HTTP_PATH")
    token = os.environ.get("DATABRICKS_TOKEN")
    if not (host and http_path and token):
        print("ERROR: Missing Databricks env vars (DATABRICKS_HOST / DATABRICKS_HTTP_PATH / DATABRICKS_TOKEN).", file=sys.stderr)
        sys.exit(2)
    return sql.connect(server_hostname=host, http_path=http_path, access_token=token)

def table_exists(conn, fqtn: str) -> bool:
    try:
        with conn.cursor() as cur:
            cur.execute(f"DESCRIBE TABLE {fqtn}")
        return True
    except Exception:
        return False

def describe_columns(conn, fqtn: str) -> List[Dict[str, str]]:
    with conn.cursor() as cur:
        cur.execute(f"DESCRIBE TABLE {fqtn}")
        rows = cur.fetchall()
    cols = []
    for r in rows:
        name = r[0]
        if name is None or (isinstance(name, str) and name.strip().startswith("#")):
            break
        cols.append({"name": r[0], "type": r[1]})
    return cols

def infer_key(table: str, cols: List[Dict[str, str]]) -> Optional[str]:
    names = [c["name"] for c in cols]
    lower = [n.lower() for n in names]
    # prefer <table>_id
    t_id = f"{table}_id".lower()
    if t_id in lower: return names[lower.index(t_id)]
    # prefer first *_id
    for n in names:
        if n.lower().endswith("_id"): return n
    # fallback "id"
    if "id" in lower: return names[lower.index("id")]
    return None

def infer_filters(cols: List[Dict[str,str]]) -> List[Dict[str,Any]]:
    filters: List[Dict[str,Any]] = []
    names_lower = [c["name"].lower() for c in cols]

    # time window on first timestamp-ish column
    ts_cols = [c["name"] for c in cols if c["type"].lower() in ("timestamp", "datetime")]
    if ts_cols:
        ts = ts_cols[0]
        filters += [
            {"name":"from_time","type":"TIMESTAMP","operator":">=","column":ts},
            {"name":"to_time","type":"TIMESTAMP","operator":"<","column":ts},
        ]

    # min/max on amount-like numeric columns
    for c in cols:
        n = c["name"].lower()
        t = c["type"].lower()
        if n in ("amount","amount_due","total","balance") and any(k in t for k in ("decimal","double","float","int","bigint")):
            filters += [
                {"name":"min_amount","type":"NUMBER","operator":">=","column":c["name"]},
                {"name":"max_amount","type":"NUMBER","operator":"<=","column":c["name"]},
            ]

    # common equality filters if present
    for cand in ("account_id","bill_id","customer_id","status","method","currency","country","email","phone"):
        if cand in names_lower:
            filters.append({"name":cand,"type":"STRING","operator":"="})

    # free-text search over a few common text cols
    text_cols = [c["name"] for c in cols if c["type"].lower() in ("string","varchar","text")]
    preferred = ("payment_id","account_id","bill_id","status","method","full_name","customer_id","country")
    pick = [c for c in text_cols if c.lower() in preferred]
    if pick:
        filters.append({"name":"q","type":"STRING","operator":"ilike_any","columns":pick[:6]})
    return filters

def write_yaml(path: Path, doc: Dict[str,Any]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        yaml.safe_dump(doc, f, sort_keys=False)
    print(f"Wrote {path}")

# -------------------- builders --------------------

def build_customer_dp(conn, catalog: str, schema: str, out_dir: Path):
    """
    Customer DP = { customer_profile, customer_accounts, customer_subscriptions }
    Relationships:
      accounts: customer_profile.customer_id -> customer_accounts.customer_id
      subscriptions: customer_accounts.account_id -> customer_subscriptions.account_id
    """
    entities = ["customer_profile","customer_accounts","customer_subscriptions"]
    present: Dict[str, Dict[str,Any]] = {}
    for t in entities:
        fqtn = f"{catalog}.{schema}.{t}"
        if not table_exists(conn, fqtn):
            print(f"WARNING: {fqtn} not found — skipping this entity", file=sys.stderr)
            continue
        cols = describe_columns(conn, fqtn)
        key = infer_key(t, cols) or "id"
        present[t] = {
            "table": "${CATALOG}.${SCHEMA}."+t,
            "key": key,
            "filters": infer_filters(cols),
        }

    if "customer_profile" not in present:
        print("ERROR: customer_profile is required for Customer DP.", file=sys.stderr)
        return

    # relationships (only add if both ends exist)
    rels = []
    if "customer_profile" in present and "customer_accounts" in present:
        rels.append({
            "name": "accounts",
            "from_entity": "customer_profile",
            "to_entity": "customer_accounts",
            "on": [{ "from": "customer_id", "to": "customer_id" }],
        })
    if "customer_accounts" in present and "customer_subscriptions" in present:
        rels.append({
            "name": "subscriptions",
            "from_entity": "customer_accounts",
            "to_entity": "customer_subscriptions",
            "on": [{ "from": "account_id", "to": "account_id" }],
        })

    doc = {
        "data_product": "customer",
        "entities": present,
        "relationships": rels,
    }
    write_yaml(out_dir / "customer.yaml", doc)

def build_payments_dp(conn, catalog: str, schema: str, out_dir: Path):
    """
    Payments DP = payments (+ bills if present) (+ adjustments if present)
    Relationships (added only if columns exist on both sides):
      - payments.account_id <-> bills.account_id
      - payments.bill_id    <-> bills.bill_id (if payments has bill_id)
    """
    base = ["payments"]
    optional = ["bills", "adjustments"]
    present: Dict[str, Dict[str,Any]] = {}

    # collect entities
    for t in base + optional:
        fqtn = f"{catalog}.{schema}.{t}"
        if not table_exists(conn, fqtn):
            if t in optional:
                print(f"NOTE: {fqtn} not found — optional, skipping", file=sys.stderr)
                continue
            else:
                print(f"ERROR: required table {fqtn} not found", file=sys.stderr)
                return
        cols = describe_columns(conn, fqtn)
        key = infer_key(t, cols) or "id"
        present[t] = {
            "table": "${CATALOG}.${SCHEMA}."+t,
            "key": key,
            "filters": infer_filters(cols),
        }

    # relationships
    rels = []
    # helper to check column presence quickly
    def has_col(entity_name: str, col: str) -> bool:
        fq = f"{catalog}.{schema}.{entity_name}"
        cols = describe_columns(conn, fq)
        return any(c["name"].lower() == col.lower() for c in cols)

    if "payments" in present and "bills" in present:
        # account_id join (if both have it)
        if has_col("payments","account_id") and has_col("bills","account_id"):
            rels.append({
                "name": "bills_by_account",
                "from_entity": "payments",
                "to_entity": "bills",
                "on": [{ "from": "account_id", "to": "account_id" }],
            })
        # bill_id join (if both have it)
        if has_col("payments","bill_id") and has_col("bills","bill_id"):
            rels.append({
                "name": "bill_ref",
                "from_entity": "payments",
                "to_entity": "bills",
                "on": [{ "from": "bill_id", "to": "bill_id" }],
            })

    doc = {
        "data_product": "payments",
        "entities": present,
        "relationships": rels,
    }
    write_yaml(out_dir / "payments.yaml", doc)

# -------------------- main CLI --------------------

def main():
    load_dotenv(override=True)
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", required=True)
    ap.add_argument("--schema", required=True)
    ap.add_argument("--out", default="registry")
    args = ap.parse_args()

    out_dir = Path(args.out)
    conn = connect_databricks()
    try:
        build_customer_dp(conn, args.catalog, args.schema, out_dir)
        build_payments_dp(conn, args.catalog, args.schema, out_dir)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
