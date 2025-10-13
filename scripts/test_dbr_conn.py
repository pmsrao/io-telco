

from databricks import sql
import os
from dotenv import load_dotenv

load_dotenv()

conn = sql.connect(
    server_hostname=os.environ["DATABRICKS_SERVER_HOSTNAME"],
    http_path=os.environ["DATABRICKS_HTTP_PATH"],
    access_token=os.environ["DATABRICKS_TOKEN"],
)
cur = conn.cursor()
cur.execute("SELECT current_user(), current_catalog(), current_schema()")
print(cur.fetchall())
cur.close(); conn.close()