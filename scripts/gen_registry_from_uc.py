#!/usr/bin/env python3
import os, yaml, argparse
from databricks import sql

# Heuristics: infer common filters
def infer_filters(cols):
    filt = []
    names = [c["name"].lower() for c in cols]
    # timestamps
    ts_cols = [c["name"] for c in cols if c["type"].lower() in ("timestamp","datetime")]
    if ts_cols:
        ts = ts_cols[0]
        filt += [
            {"name":"from_time","type":"TIMESTAMP","operator":">=","column":ts},
            {"name":"to_time","type":"TIMESTAMP","operator":"<","column":ts},
        ]
    # amount-ish
    for c in cols:
        if c["name"].lower() in ("amount","amount_due","total","balance") and c["type"].lower() in ("double","float","decimal","int","bigint"):
            filt += [
                {"name":"min_amount","type":"NUMBER","operator":">=","column":c["name"]},
                {"name":"max_amount","type":"NUMBER","operator":"<=","column":c["name"]},
            ]
    # common ids
    for cand in ("account_id","bill_id","customer_id","status","method","currency","country"):
        if cand in names:
            filt.append({"name":cand,"type":"STRING","operator":"="})
    # q search across a few text columns
    text_cols = [c["name"] for c in cols if c["type"].lower() in ("string","varchar","text")]
    keep = [c for c in text_cols if c.lower() in ("payment_id","account_id","bill_id","status","method","full_name","customer_id","country")]
    if keep:
        filt.append({"name":"q","type":"STRING","operator":"ilike_any","columns":keep[:6]})
    return filt

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", required=True)
    ap.add_argument("--schema", required=True)
    ap.add_argument("--table", required=True)     # e.g., payments
    ap.add_argument("--key", required=True)       # e.g., payment_id
    ap.add_argument("--dp", required=True)        # e.g., payments
    ap.add_argument("--out", default="registry")
    args = ap.parse_args()

    conn = sql.connect(
        server_hostname=os.environ["DATABRICKS_HOST"],
        http_path=os.environ["DATABRICKS_HTTP_PATH"],
        access_token=os.environ["DATABRICKS_TOKEN"],
    )
    with conn, conn.cursor() as cur:
        cur.execute(f'DESCRIBE TABLE {args.catalog}.{args.schema}.{args.table}')
        rows = cur.fetchall()
    # rows: name, type, comment (stop at the partition/metadata divider)
    cols = []
    for r in rows:
        name = r[0]
        if name is None or name.strip().lower() in ("# partitioning","# detailed table information"):
            break
        cols.append({"name": name, "type": r[1]})

    doc = {
        "data_product": args.dp,
        "entities": {
            args.table: {
                "table": f"${{CATALOG}}.${{SCHEMA}}.{args.table}",
                "key": args.key,
                "filters": infer_filters(cols),
            }
        }
    }
    os.makedirs(args.out, exist_ok=True)
    path = os.path.join(args.out, f"{args.dp}.yaml")
    with open(path, "w") as f:
        yaml.safe_dump(doc, f, sort_keys=False)
    print(f"Wrote {path}")

if __name__ == "__main__":
    main()
