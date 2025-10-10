import os
from dotenv import load_dotenv
load_dotenv()

CATALOG = os.getenv("CATALOG", "telco")
SCHEMA  = os.getenv("SCHEMA",  "silver")
REGISTRY_DIR = os.getenv("DP_REGISTRY", "registry")

def fq(name: str) -> str:
    """Return fully-qualified {catalog}.{schema}.{name} if not already qualified."""
    if "." in name:
        return name
    return f"{CATALOG}.{SCHEMA}.{name}"
