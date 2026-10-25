"""Start with uvicorn app.main:app --host 127.0.0.1 --workers 1."""
import os
from contextlib import asynccontextmanager
from uuid import uuid4
from fastapi import FastAPI, Request
from starlette.responses import JSONResponse
from app.api.runtime import router
from app.storage import registry
from app.core.config import settings
from app.core.logging import configure_logging

# Application-specific files explicitly disable external LangChain tracing.
os.environ['LANGCHAIN_TRACING_V2'] = 'false'
os.environ['LANGSMITH_TRACING'] = 'false'


class UploadRequestLimit:
    """Bound request bodies before multipart parsing, regardless of Content-Length."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or scope['method'] not in {'POST', 'PUT', 'PATCH'}:
            return await self.app(scope, receive, send)
        limit = 5 * settings.max_file_size + 64 * 1024 if scope['path'].startswith('/documents') else 32_000
        messages, total = [], 0
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect':
                return
            total += len(message.get('body', b''))
            if total > limit:
                return await JSONResponse({'detail': 'Request exceeds configured size limit'}, status_code=413)(scope, receive, send)
            messages.append(message)
            if not message.get('more_body', False):
                break
        async def replay():
            return messages.pop(0) if messages else await receive()
        await self.app(scope, replay, send)


@asynccontextmanager
async def lifespan(app):
    import fcntl
    registry.ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (registry.ROOT / 'backend.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('Only one backend worker/process is supported') from None
        registry.initialize()
        registry.recover()
        yield
        fcntl.flock(lock, fcntl.LOCK_UN)


configure_logging()
app = FastAPI(title='AI Security Document Assistant', lifespan=lifespan)
app.add_middleware(UploadRequestLimit)
app.include_router(router)


@app.middleware('http')
async def request_id(request: Request, call_next):
    identifier = str(uuid4())
    try:
        response = await call_next(request)
    except Exception:
        response = JSONResponse({'detail': 'Operational error; no fallback result', 'request_id': identifier}, status_code=500)
    response.headers['X-Request-ID'] = identifier
    return response
