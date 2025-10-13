import time, re, uuid, json
from typing import List

class Redactor:
    def __init__(self, patterns: List[str]):
        self.regexes = [re.compile(p) for p in (patterns or [])]
    def redact(self, s: str) -> str:
        for rgx in self.regexes:
            s = rgx.sub("[REDACTED]", s)
        return s

def with_request_context(handler):
    async def wrapper(request, *args, **kwargs):
        cid = request.headers.get("x-correlation-id", str(uuid.uuid4()))
        request.state.correlation_id = cid
        t0 = time.time()
        try:
            resp = await handler(request, *args, **kwargs)
            return resp
        finally:
            dt = int((time.time()-t0)*1000)
            print(json.dumps({"cid": cid, "ms": dt, "path": request.url.path}))
    return wrapper
