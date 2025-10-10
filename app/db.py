import os
from typing import Any, Dict, List
import databricks.sql as dbsql
from dotenv import load_dotenv
load_dotenv()

DATABRICKS_HOST = os.getenv("DATABRICKS_HOST")
DATABRICKS_HTTP_PATH = os.getenv("DATABRICKS_HTTP_PATH")
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN")

def query(sql_text: str, params: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
    if not (DATABRICKS_HOST and DATABRICKS_HTTP_PATH and DATABRICKS_TOKEN):
        raise RuntimeError("Databricks env vars not set")
    with dbsql.connect(server_hostname=DATABRICKS_HOST,
                       http_path=DATABRICKS_HTTP_PATH,
                       access_token=DATABRICKS_TOKEN) as conn:
        with conn.cursor() as cur:
            cur.execute(sql_text, params or {})
            cols = [c[0] for c in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
