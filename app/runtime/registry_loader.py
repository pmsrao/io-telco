import os, glob, yaml
from typing import Dict, Any

class Registry:
    def __init__(self, root: str = "registry"):
        self.root = root
        self.settings = self._load_yaml(os.path.join(root, "_settings.yaml"))
        self.docs = self._load_all()
    def _load_yaml(self, p: str) -> Dict[str,Any]:
        with open(p, "r") as f:
            return yaml.safe_load(f) or {}
    def _load_all(self):
        docs = []
        for p in glob.glob(os.path.join(self.root, "*.yaml")):
            if p.endswith("_settings.yaml"): continue
            docs.append(self._load_yaml(p))
        print(docs)
        return docs
    def env(self) -> Dict[str,str]:
        vars = (self.settings.get("globals", {}).get("template_vars") or [])
        return {k: os.environ.get(k, "") for k in vars}
    def policies(self) -> Dict[str,str]:
        return (self.settings.get("globals", {}).get("policies") or {})
    def globals(self) -> Dict[str,Any]:
        return (self.settings.get("globals") or {})
    
    def entities(self):
        for doc in self.docs:
            dpn = doc.get("data_product")
            ents = (doc.get("entities") or {})
            # Accept dict or list forms
            if isinstance(ents, dict):
                for name, spec in ents.items():
                    yield dpn, name, spec
            elif isinstance(ents, list):
                for item in ents:
                    # list of {name: spec} objects
                    if isinstance(item, dict) and "name" not in item:
                        for name, spec in item.items():
                            yield dpn, name, spec
                    # list of {"name": "...", "spec": {...}} objects
                    elif isinstance(item, dict) and "name" in item and "spec" in item:
                        yield dpn, item["name"], item["spec"]
                    else:
                        # ignore malformed entries
                        continue
            else:
                # nothing usable
                continue


    def relationships(self):
        for doc in self.docs:
            for rel in (doc.get("relationships") or []):
                yield rel

# ---------- put this at module level (no indentation) ----------
if __name__ == "__main__":
    import json, sys
    root = sys.argv[1] if len(sys.argv) > 1 else "registry"
    reg = Registry(root=root)
    summary = []
    for dp, ent, spec in reg.entities():
        cols = spec.get("columns")
        if isinstance(cols, dict):
            col_count = len(cols)
            col_type = "dict"
        elif isinstance(cols, list):
            col_count = len(cols)
            col_type = "list"
        else:
            col_count = 0
            col_type = "none"
        summary.append({
            "data_product": dp,
            "entity": ent,
            "table": spec.get("table"),
            "columns_type": col_type,
            "columns_count": col_count,
        })
    print(json.dumps(summary, indent=2))