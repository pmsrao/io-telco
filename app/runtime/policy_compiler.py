from typing import Dict, Any, List
from jinja2 import Template

class PolicyCompiler:
    def __init__(self, policies: Dict[str,str]):
        self.policies = policies or {}
    def render(self, name: str, ctx: Dict[str,Any]):
        raw = self.policies.get(name)
        if not raw:
            raise KeyError(f"Unknown policy: {name}")
        return Template(raw).render(**ctx)
    def compose_where(self, names: List[str], ctx: Dict[str,Any]):
        parts = [self.render(n, ctx) for n in (names or [])]
        return " AND ".join([p for p in parts if p])
