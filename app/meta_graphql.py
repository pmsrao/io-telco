# app/meta_graphql.py
from __future__ import annotations

import os
import re
import json
from dataclasses import make_dataclass, field as dc_field, fields as dc_fields
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import strawberry
from fastapi import APIRouter
from strawberry.fastapi import GraphQLRouter
from strawberry.schema.config import StrawberryConfig 
from dotenv import load_dotenv

load_dotenv()

# ===== Databricks SQL connector =====
try:
    from databricks import sql as dbsql
except Exception:  # pragma: no cover
    dbsql = None

# --------------------------------------------------------------------------------------
# Registry loader (+ validation)
# --------------------------------------------------------------------------------------

def load_registry(dir_path: str = "registry") -> Dict[str, Dict[str, Any]]:
    """Load *.yaml in registry/, normalize shapes."""
    import yaml

    reg: Dict[str, Dict[str, Any]] = {}
    for p in Path(dir_path).glob("*.yaml"):
        with p.open() as f:
            data = yaml.safe_load(f) or {}

        dp = data.get("data_product") or data.get("product") or data.get("name") or p.stem
        data["data_product"] = dp

        ents = data.get("entities") or {}
        if isinstance(ents, list):
            merged = {}
            for item in ents:
                if not isinstance(item, dict):
                    raise ValueError(f"{p.name}: entities list item must be a mapping, got {type(item).__name__}")
                merged.update(item)
            ents = merged
        if not isinstance(ents, dict):
            raise ValueError(f"{p.name}: entities must be a mapping, got {type(ents).__name__}")
        data["entities"] = ents

        rels = data.get("relationships") or []
        if not isinstance(rels, list):
            raise ValueError(f"{p.name}: relationships must be a list, got {type(rels).__name__}")
        data["relationships"] = rels

        reg[dp] = data

    if not reg:
        raise RuntimeError(f"No registry YAMLs found in {dir_path}/")
    return reg


def _assert_entity(dp: str, en: str, meta: Dict[str, Any]) -> None:
    if not isinstance(meta, dict):
        raise ValueError(f"Entity '{en}' in DP '{dp}' must be a mapping, got {type(meta).__name__}")
    for req in ("table", "key"):
        if req not in meta:
            raise ValueError(f"Entity '{en}' in DP '{dp}' missing required field '{req}'")
    if meta.get("filters") is None:
        meta["filters"] = []
    if not isinstance(meta["filters"], list):
        raise ValueError(f"Entity '{en}' in DP '{dp}': 'filters' must be a list")

# --------------------------------------------------------------------------------------
# Env helpers / Databricks helpers
# --------------------------------------------------------------------------------------

def _sub_table_env(s: str) -> str:
    cat = os.getenv("CATALOG")
    sch = os.getenv("SCHEMA")
    s = s.replace("${CATALOG}", cat or "${CATALOG}")
    s = s.replace("${SCHEMA}", sch or "${SCHEMA}")
    return s

def _connect():
    if dbsql is None:
        raise RuntimeError("databricks-sql-connector not installed")
    host = os.getenv("DATABRICKS_SERVER_HOSTNAME")
    http_path = os.getenv("DATABRICKS_HTTP_PATH")
    token = os.getenv("DATABRICKS_TOKEN")
    if not (host and http_path and token):
        raise RuntimeError("Missing DATABRICKS_HOST / DATABRICKS_HTTP_PATH / DATABRICKS_TOKEN")
    return dbsql.connect(server_hostname=host, http_path=http_path, access_token=token)

def _describe_columns(fqtn: str) -> List[Dict[str, str]]:
    fqtn = _sub_table_env(fqtn)
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(f"DESCRIBE TABLE {fqtn}")
        rows = cur.fetchall()
    cols: List[Dict[str, str]] = []
    for r in rows:
        name = r[0]
        if name is None or (isinstance(name, str) and name.strip().startswith("#")):
            break
        cols.append({"name": r[0], "type": r[1]})
    return cols

def _fetch_all(sql_text: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(sql_text, params)
        rows = cur.fetchall()
        headers = [d[0] for d in cur.description] if getattr(cur, "description", None) else []
    out: List[Dict[str, Any]] = []
    for tup in rows:
        out.append({headers[i]: tup[i] for i in range(len(headers))})
    return out

# --------------------------------------------------------------------------------------
# WHERE compiler (metadata-driven)
# --------------------------------------------------------------------------------------

FILTER_OPS: Dict[str, str] = {
    "=": "{col} = :{p}",
    "!=": "{col} <> :{p}",
    ">": "{col} > :{p}",
    ">=": "{col} >= :{p}",
    "<": "{col} < :{p}",
    "<=": "{col} <= :{p}",
    "ilike": "{col} ILIKE :{p}",
}

def _compile_where(filters_def: List[Dict[str, Any]], filters_in: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    clauses: List[str] = []
    params: Dict[str, Any] = {}
    defs = {f["name"]: f for f in (filters_def or [])}

    for fname, fval in (filters_in or {}).items():
        spec = defs.get(fname)
        if spec is None or fval is None:
            continue
        op = (spec.get("operator") or spec.get("op") or "=").lower()

        if op == "ilike_any":
            like_val = f"%{fval}%"
            ors = []
            for i, c in enumerate(spec["columns"]):
                p = f"p_{fname}_{i}"
                ors.append(f"{c} ILIKE :{p}")
                params[p] = like_val
            clauses.append("(" + " OR ".join(ors) + ")")
            continue

        col = spec.get("column") or fname
        if op == "ilike":
            fval = f"%{fval}%"

        fmt = FILTER_OPS.get(op, FILTER_OPS["="])
        p = f"p_{fname}"
        params[p] = fval
        clauses.append(fmt.format(col=col, p=p))

    where = " AND ".join(clauses)
    return (("WHERE " + where) if where else ""), params

# --------------------------------------------------------------------------------------
# Type factories
# --------------------------------------------------------------------------------------

def _to_pascal(s: str) -> str:
    parts = re.split(r"[_\W]+", s.strip())
    return "".join(p[:1].upper() + p[1:] for p in parts if p)

def _py_type_for_sql(sqltype: str):
    t = (sqltype or "").lower()
    if "int" in t:
        return Optional[int]
    if any(x in t for x in ("double", "float", "decimal", "real", "numeric")):
        return Optional[float]
    if "timestamp" in t or "date" in t or "time" in t:
        return Optional[str]  # present timestamps as ISO strings
    return Optional[str]

def _build_entity_type(dp_name: str, en_name: str, columns: List[Dict[str, str]]):
    type_name = _to_pascal(dp_name) + _to_pascal(en_name)
    fields_spec = []
    for c in columns:
        col = c["name"]
        py_t = _py_type_for_sql(c["type"])
        fields_spec.append((col, py_t, dc_field(default=None)))
    PyCls = make_dataclass(type_name, fields_spec, frozen=False)
    GQLCls = strawberry.type(PyCls)
    # publish globally so Strawberry can resolve by name
    globals()[GQLCls.__name__] = GQLCls
    return GQLCls

def _build_filter_input_type(dp_name: str, en_name: str, filters_def: List[Dict[str, Any]]):
    input_name = _to_pascal(dp_name) + _to_pascal(en_name) + "Filter"
    fields_spec = []
    for f in (filters_def or []):
        fname = f["name"]
        ftype = (f.get("type") or "STRING").upper()
        if ftype in ("NUMBER", "FLOAT", "DOUBLE", "DECIMAL", "INT", "INTEGER", "BIGINT"):
            py_t = Optional[float]
        elif ftype in ("TIMESTAMP", "DATETIME", "DATE", "TIME"):
            py_t = Optional[str]
        else:
            py_t = Optional[str]
        fields_spec.append((fname, py_t, dc_field(default=None)))

    if not fields_spec:
        fields_spec = [("dummy", Optional[str], dc_field(default=None))]

    PyInput = make_dataclass(input_name, fields_spec, frozen=False)
    GQLInput = strawberry.input(PyInput)
    globals()[GQLInput.__name__] = GQLInput
    return GQLInput

# --------------------------------------------------------------------------------------
# Resolver wrappers (global, with real annotations Strawberry can resolve)
# --------------------------------------------------------------------------------------

# We store impls in a global dict and generate thin global wrappers with proper annotations.
_RESOLVER_IMPLS: Dict[str, Any] = {}

def _make_global_get_wrapper(func_name: str, type_name: str):
    g = globals()
    _RESOLVER_IMPLS[func_name] = _RESOLVER_IMPLS[func_name]  # ensure key exists
    src = (
        f"from typing import Optional\n"
        f"def {func_name}(key: str) -> Optional[{type_name}]:\n"
        f"    return _RESOLVER_IMPLS['{func_name}'](key)\n"
    )
    exec(src, g)
    return g[func_name]

def _make_global_list_wrapper(func_name: str, type_name: str, filter_input_name: str):
    g = globals()
    _RESOLVER_IMPLS[func_name] = _RESOLVER_IMPLS[func_name]
    src = (
        f"from typing import List, Optional\n"
        f"def {func_name}(filters: Optional[{filter_input_name}] = None, limit: int = 50, offset: int = 0) -> List[{type_name}]:\n"
        f"    return _RESOLVER_IMPLS['{func_name}'](filters, limit, offset)\n"
    )
    exec(src, g)
    return g[func_name]

# --------------------------------------------------------------------------------------
# Schema builder
# --------------------------------------------------------------------------------------

def _build_dynamic_query_type():
    registry = load_registry()
    query_fields: Dict[str, Any] = {}

    # caches
    table_cols_cache: Dict[str, List[Dict[str, str]]] = {}
    entity_types: Dict[str, Any] = {}
    filter_types: Dict[str, Any] = {}

    for dp_name, dp_cfg in registry.items():
        entities = dp_cfg.get("entities") or {}
        for en_name, en_meta in entities.items():
            _assert_entity(dp_name, en_name, en_meta)

            table = en_meta["table"]
            key_col = en_meta["key"]
            filters_def = en_meta.get("filters", [])

            fqtn = table
            cols = table_cols_cache.get(fqtn)
            if cols is None:
                cols = _describe_columns(fqtn)
                table_cols_cache[fqtn] = cols

            t_key = f"{dp_name}.{en_name}"

            GQLEnt = entity_types.get(t_key)
            if GQLEnt is None:
                GQLEnt = _build_entity_type(dp_name, en_name, cols)
                entity_types[t_key] = GQLEnt

            GQLFilter = filter_types.get(t_key)
            if GQLFilter is None:
                GQLFilter = _build_filter_input_type(dp_name, en_name, filters_def)
                filter_types[t_key] = GQLFilter

            # ---- build SQL strings once for speed ----
            col_names = [c["name"] for c in cols]
            cols_sql = ", ".join(col_names)
            table_sql = _sub_table_env(table)

            # --------- resolver impls (not visible to Strawberry) ---------
            def get_impl_factory(_cols_sql=cols_sql, _table_sql=table_sql, _key_col=key_col, _GQLEnt=GQLEnt):
                def _impl(key: str):
                    sql = f"SELECT {_cols_sql} FROM {_table_sql} WHERE {_key_col} = :key LIMIT 1"
                    rows = _fetch_all(sql, {"key": key})
                    if not rows:
                        return None
                    return _GQLEnt(**rows[0])
                return _impl

            def list_impl_factory(_cols_sql=cols_sql, _table_sql=table_sql, _filters_def=filters_def, _GQLEnt=GQLEnt, _GQLFilter=GQLFilter):
                def _impl(filters: Optional[_GQLFilter] = None, limit: int = 50, offset: int = 0):
                    fdict: Dict[str, Any] = {}
                    if filters is not None:
                        for f in dc_fields(_GQLFilter):
                            k = f.name
                            if hasattr(filters, k):
                                v = getattr(filters, k)
                                if v is not None:
                                    fdict[k] = v
                    where_sql, bind = _compile_where(_filters_def, fdict)
                    bind["lim"] = int(limit)
                    bind["off"] = int(offset)
                    sql = f"SELECT {_cols_sql} FROM {_table_sql} {where_sql} LIMIT :lim OFFSET :off"
                    rows = _fetch_all(sql, bind)
                    return [_GQLEnt(**r) for r in rows]
                return _impl

            # store impls globally and create global wrappers with proper annotations
            if en_name.endswith("s"):
                singular = en_name[:-1]
            else:
                singular = en_name

            get_field_name = f"get_{singular}"
            list_field_name = f"list_{en_name}"

            # uniquify if collision
            if get_field_name in query_fields:
                get_field_name = f"{get_field_name}_{dp_name}"
            if list_field_name in query_fields:
                list_field_name = f"{list_field_name}_{dp_name}"

            # Register impls
            get_impl_name = f"__impl_{get_field_name}"
            list_impl_name = f"__impl_{list_field_name}"
            _RESOLVER_IMPLS[get_impl_name] = get_impl_factory()
            _RESOLVER_IMPLS[list_impl_name] = list_impl_factory()

            # Create global wrappers with real annotations Strawberry can resolve
            get_wrapper = _make_global_get_wrapper(get_impl_name, GQLEnt.__name__)
            list_wrapper = _make_global_list_wrapper(list_impl_name, GQLEnt.__name__, GQLFilter.__name__)

            # Attach to Query fields
            query_fields[get_field_name] = strawberry.field(resolver=get_wrapper)
            query_fields[list_field_name] = strawberry.field(resolver=list_wrapper)

    # Build Query type
    QueryCls = type("Query", (), query_fields)
    Query = strawberry.type(QueryCls)
    return Query

def build_dynamic_schema() -> strawberry.Schema:
    Query = _build_dynamic_query_type()
    return strawberry.Schema(
        query=Query,
        config=StrawberryConfig(auto_camel_case=False),
    )

def build_dynamic_router(path: str = "/graphql") -> APIRouter:
    schema = build_dynamic_schema()
    router = GraphQLRouter(schema, path=path)
    return router
