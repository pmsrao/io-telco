#!/usr/bin/env python3
import os, json, time, argparse, requests
from pathlib import Path

def get_args():
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--skip-unreachable", action="store_true")
    p.add_argument("--retries", type=int, default=2)
    p.add_argument("--health", default="/health")
    return p.parse_args()

def health_check(reg_url: str, health_path: str, headers: dict) -> bool:
    if not health_path:
        return True
    try:
        base = reg_url.rstrip("/")
        if base.endswith("/register"):
            base = base[: -len("/register")]
        r = requests.get(base + health_path, headers=headers, timeout=5)
        return r.status_code < 500
    except Exception:
        return False

def main():
    args = get_args()
    contracts_dir = Path("contracts")
    manifest_path = contracts_dir / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit("contracts/manifest.json not found. Run scripts/export_contracts.py first.")

    mcp_url = os.getenv("MCP_URL", "http://127.0.0.1:9000/register")
    token = os.getenv("MCP_AUTH_TOKEN")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    manifest = json.loads(manifest_path.read_text())
    service_url = manifest.get("service_url") or os.getenv("SERVICE_URL", "http://127.0.0.1:8000/graphql")
    sha = manifest.get("git_sha", "unknown")

    if not args.dry_run and not health_check(mcp_url, args.health, headers):
        msg = f"[mcp] {mcp_url} not reachable (health failed)."
        if args.skip_unreachable:
            print(msg, "Skipping."); return
        raise SystemExit(msg + " Start MCP or use --dry-run/--skip-unreachable.")

    for p in manifest.get("products", []):
        name = p["data_product"]
        graphql_text = Path(p["graphql"]).read_text()
        openapi_text = Path(p["openapi"]).read_text()
        payload = {
            "name": name,
            "type": "data-product",
            "interfaces": [
                {"kind": "graphql", "contract": graphql_text, "endpoint": service_url},
                {"kind": "openapi", "contract": openapi_text, "endpoint": service_url},
            ],
            "metadata": {"source": "registry", "git_sha": sha, "version": "v1"},
        }

        if args.dry_run:
            print(f"\n[mcp][dry-run] Would POST {mcp_url} with payload:")
            print(json.dumps(payload, indent=2)[:2000], "...\n")
            continue

        attempt = 0
        while True:
            attempt += 1
            try:
                print(f"[mcp] registering {name} -> {mcp_url} (attempt {attempt})")
                resp = requests.post(mcp_url, headers=headers, json=payload, timeout=20)
                print("  ->", resp.status_code, resp.text[:400])
                if resp.ok:
                    break
                if attempt >= args.retries + 1:
                    raise SystemExit(f"[mcp] registration failed for {name}: {resp.status_code} {resp.text}")
                time.sleep(1.5 * attempt)
            except requests.exceptions.RequestException as e:
                if attempt >= args.retries + 1:
                    if args.skip_unreachable:
                        print(f"[mcp] {name}: connection error after retries: {e}. Skipping.")
                        break
                    raise
                print(f"[mcp] connection error: {e}. Retrying...")
                time.sleep(1.5 * attempt)

    print("✅ MCP registration complete.")

if __name__ == "__main__":
    main()