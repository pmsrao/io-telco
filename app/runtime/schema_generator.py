"""
GraphQL SDL generator from registry:
- Emits entity types
- Emits Query with canonical list_<entity> fields
- Adds aliases from registry (e.g., list_customers) without duplicating canonical names
- Each field supports both `filter` and `where` args (resolver can map where→filter)
"""

from typing import Dict, Any, List


class SchemaGenerator:
    def __init__(self):
        pass

    def entity_type(self, entity: str, spec: Dict[str, Any]) -> str:
        cols = spec.get("columns") or {}
        lines: List[str] = []
        for col, meta in cols.items():
            scalar = meta.get("scalar", "String")
            lines.append(f"  {col}: {scalar}")
        body = "\n".join(lines) if lines else "  _empty: String"
        return f"type {entity} {{\n{body}\n}}\n"

    def _query_fields_for_entity(self, entity: str, spec: Dict[str, Any]) -> List[str]:
        """
        For each entity produce:
          - canonical: list_<entity>(..., filter: JSON, where: JSON)
          - aliases  : alias(..., filter: JSON, where: JSON)   (skip if alias == canonical)
        """
        fields: List[str] = []
        canonical = f"list_{entity}"
        arglist = "(limit: Int, offset: Int, order_by: [OrderBy!], filter: JSON, where: JSON)"

        # Canonical
        fields.append(f"  {canonical}{arglist}: [{entity}!]")

        # Aliases (dedupe canonical)
        for alias in (spec.get("aliases") or []):
            if not isinstance(alias, str):
                continue
            if alias == canonical:
                # skip exact duplicate names
                continue
            if alias.startswith("list_"):
                fields.append(f"  {alias}{arglist}: [{entity}!]")
            elif alias.startswith("get_"):
                # if/when you expose get_ aliases, you can add their args here
                fields.append(f"  {alias}(id: ID!): {entity}")

        return fields

    def stitch(self, registry) -> str:
        scalars = """scalar Decimal
scalar Timestamp
scalar JSON

input OrderBy { field: String!, dir: String }

"""
        parts: List[str] = [scalars]
        qfields: List[str] = []

        for dp, ent, spec in registry.entities():
            parts.append(self.entity_type(ent, spec))
            qfields.extend(self._query_fields_for_entity(ent, spec))

        query = "type Query {\n" + "\n".join(qfields) + "\n}\n"
        parts.append(query)

        sdl = "\n".join(parts)
        return sdl


# CLI entrypoint
if __name__ == "__main__":
    import sys
    from app.runtime.registry_loader import Registry

    root = sys.argv[1] if len(sys.argv) > 1 else "registry"
    reg = Registry(root=root)
    sdl = SchemaGenerator().stitch(reg)
    print(sdl)
