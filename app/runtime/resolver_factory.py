from typing import Any, Dict, List, Tuple
from ariadne import QueryType
from decimal import Decimal
import os, re

# Robust .env load
try:
    from dotenv import load_dotenv, find_dotenv
    _env = find_dotenv(usecwd=True)
    if _env:
        load_dotenv(_env)
except Exception:
    pass

class ResolverFactory:
    def __init__(self, registry):
        self.registry = registry

    # Expand ${VARNAME} (CATALOG, SCHEMA, TENANT, etc.) in table paths
    def _expand_env_vars(self, s: str) -> str:
        if not s:
            return s
        def repl(m):
            key = m.group(1)
            return os.getenv(key, m.group(0))
        return re.sub(r"\$\{([A-Z_][A-Z0-9_]*)\}", repl, s)

    def _get_db_env(self) -> Tuple[str, str, str]:
        host = os.getenv("DATABRICKS_SERVER_HOSTNAME")
        path = os.getenv("DATABRICKS_HTTP_PATH")
        token = os.getenv("DATABRICKS_TOKEN")
        missing = [k for k, v in {
            "DATABRICKS_SERVER_HOSTNAME": host,
            "DATABRICKS_HTTP_PATH": path,
            "DATABRICKS_TOKEN": token,
        }.items() if not v]
        if missing:
            raise RuntimeError(
                "Databricks env not set: " + ", ".join(missing) +
                "\nSet via `.env` or export in shell, or run uvicorn with --env-file .env"
            )
        return host, path, token

    def _compose_where_and_params(self, spec: Dict[str, Any], flt: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        where_parts: List[str] = []
        params: Dict[str, Any] = {}
        for f in (spec.get("filters") or []):
            name = f.get("name")
            if not name or (flt is None) or (name not in flt):
                continue
            op = (f.get("op") or f.get("operator") or "=").upper()
            col = f.get("column") or name
            val = flt[name]
            if op == "ILIKE" and isinstance(val, str):
                where_parts.append(f"LOWER({col}) LIKE :{name}")
                params[name] = f"%{val.lower()}%"
            elif op == "ILIKE_ANY":
                vals = val if isinstance(val, list) else [val]
                where_parts.append("(" + " OR ".join([f"LOWER({col}) LIKE :{name}_{i}" for i,_ in enumerate(vals)]) + ")")
                for i, v in enumerate(vals):
                    params[f"{name}_{i}"] = f"%{str(v).lower()}%"
            elif op == "BETWEEN" and isinstance(val, (list, tuple)) and len(val) == 2:
                where_parts.append(f"{col} BETWEEN :{name}_lo AND :{name}_hi")
                params[f"{name}_lo"] = val[0]; params[f"{name}_hi"] = val[1]
            else:
                where_parts.append(f"{col} {op} :{name}")
                params[name] = val
        return " AND ".join(where_parts), params

    def _execute_rows(
        self,
        table: str,
        columns: List[str],
        where_sql: str,
        params: Dict[str, Any],
        order_by: List[Dict[str, str]],
        limit: int,
        offset: int,
    ) -> List[Dict[str, Any]]:
        from databricks import sql as dbr
        resolved_table = self._expand_env_vars(table)
        select_cols = ", ".join(columns) if columns else "*"
        query = f"SELECT {select_cols} FROM {resolved_table}"
        if where_sql:
            query += f" WHERE {where_sql}"
        if order_by:
            parts = [f"{ob.get('field')} {ob.get('dir','ASC')}" for ob in order_by if ob.get('field')]
            if parts:
                query += " ORDER BY " + ", ".join(parts)
        query += f" LIMIT {int(limit)} OFFSET {int(offset)}"
        print(f"[SQL] {query} :: {params}")
        host, path, token = self._get_db_env()
        rows: List[Dict[str, Any]] = []
        with dbr.connect(server_hostname=host, http_path=path, access_token=token) as conn:
            cur = conn.cursor()
            cur.execute(query, params or {})
            colnames = [d[0] for d in cur.description] if cur.description else []
            for r in cur.fetchall():
                safe = {}
                for c, v in zip(colnames, r):
                    if isinstance(v, Decimal):
                        safe[c] = float(v)
                    elif isinstance(v, bytes):
                        safe[c] = v.decode("utf-8", errors="ignore")
                    else:
                        safe[c] = v
                rows.append(safe)
        return rows

    def _mk_list(self, ent: str, spec: Dict[str, Any]):
        table = spec.get("table")
        cols = list((spec.get("columns") or {}).keys())
        def resolver(*_, limit=None, offset=None, order_by=None, filter=None, where=None):
            # where → filter
            if where is not None and filter is None:
                filter = where
            # pagination defaults
            pg = (spec.get("pagination") or {})
            if limit is None:
                limit = pg.get("default_limit", 200)
            max_limit = pg.get("max_limit", 2000)
            limit = min(int(limit), int(max_limit))
            offset = int(offset) if offset is not None else 0
            # default order_by
            if not order_by:
                ob_default = spec.get("order_by_default")
                if ob_default:
                    direction = "DESC" if ob_default.startswith("-") else "ASC"
                    field = ob_default.lstrip("-")
                    order_by = [{"field": field, "dir": direction}]
            where_sql, params = self._compose_where_and_params(spec, filter or {})
            return self._execute_rows(table, cols, where_sql, params, order_by or [], limit, offset)
        return resolver

    def build(self, query: QueryType = None) -> QueryType:
        q = query or QueryType()
        for dp, ent, spec in self.registry.entities():
            q.set_field(f"list_{ent}", self._mk_list(ent, spec))
            for alias in (spec.get("aliases") or []):
                if isinstance(alias, str) and alias.startswith("list_"):
                    q.set_field(alias, self._mk_list(ent, spec))
        return q