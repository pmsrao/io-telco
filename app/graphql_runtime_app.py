from fastapi import FastAPI, Request
from ariadne.asgi import GraphQL
from ariadne import make_executable_schema, load_schema_from_path
from app.runtime.registry_loader import Registry
from app.runtime.schema_generator import SchemaGenerator
from app.runtime.resolver_factory import ResolverFactory

from databricks import sql as dbr
import os

app = FastAPI()

# Health: env + optional DB ping
@app.get("/health")
def health():
    missing = [k for k in ("DATABRICKS_SERVER_HOSTNAME","DATABRICKS_HTTP_PATH","DATABRICKS_TOKEN") if not os.getenv(k)]
    status = {"ok": len(missing) == 0, "missing_env": missing}
    try:
        if not missing:
            with dbr.connect(
                server_hostname=os.getenv("DATABRICKS_SERVER_HOSTNAME"),
                http_path=os.getenv("DATABRICKS_HTTP_PATH"),
                access_token=os.getenv("DATABRICKS_TOKEN"),
            ) as conn:
                cur = conn.cursor()
                cur.execute("SELECT 1")
                cur.fetchall()
            status["db"] = "ok"
    except Exception as e:
        status["db"] = f"error: {e.__class__.__name__}"
        status["ok"] = False
    return status

# Optional auth guard (no-op for now)
@app.middleware("http")
async def auth_guard(request: Request, call_next):
    if request.url.path == "/graphql":
        _auth = request.headers.get("authorization")
        # TODO: validate if you enforce app-level tokens
    return await call_next(request)

# Build schema at import
registry = Registry(root="registry")
sg = SchemaGenerator()
sdl = sg.stitch(registry)

schema = make_executable_schema(sdl)
resolvers = ResolverFactory(registry).build()

from ariadne import make_executable_schema, ObjectType

query = resolvers or ObjectType("Query")

app.mount(
    "/graphql",
    GraphQL(
        schema,
        debug=True,
        context_value=lambda req: {"request": req},
    ),
)