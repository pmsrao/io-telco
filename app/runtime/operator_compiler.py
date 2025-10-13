from typing import Dict, Any, Tuple

class OpCompiler:
    """Declarative mapping of filter ops → SQL fragments."""
    def __init__(self):
        self.handlers = {
            "=": lambda c,p: (f"{c} = :{p}", {p: None}),
            "in": lambda c,p: (f"{c} IN :{p}", {p: []}),
            ">=": lambda c,p: (f"{c} >= :{p}", {p: None}),
            "<=": lambda c,p: (f"{c} <= :{p}", {p: None}),
            "ilike_any": self._ilike_any,
            "between":  self._between,
            "regex":    lambda c,p: (f"REGEXP_LIKE({c}, :{p})", {p: None}),
        }
    def compile(self, spec: Dict[str,Any], param_name: str):
        op = spec.get("op")
        col = spec.get("column") or spec.get("name")
        if op not in self.handlers:
            raise ValueError(f"Unsupported op: {op}")
        return self.handlers[op](col, param_name)
    def _ilike_any(self, col, p):
        return (f"(LOWER({col}) LIKE ANY(:{p}))", {p: []})
    def _between(self, col, p):
        return (f"{col} BETWEEN :{p}_lo AND :{p}_hi", {f"{p}_lo": None, f"{p}_hi": None})
