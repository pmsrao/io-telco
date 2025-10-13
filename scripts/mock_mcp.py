# scripts/mock_mcp.py
from fastapi import FastAPI, Request
from pydantic import BaseModel
import uvicorn

app = FastAPI()

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/register")
async def register(req: Request):
    body = await req.json()
    # pretend to persist; echo summary
    return {"status": "ok", "name": body.get("name"), "ops": len(body.get("operations", []))}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=9000)
