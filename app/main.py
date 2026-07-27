from fastapi import FastAPI
from uuid import uuid4
from time import perf_counter

from app.api.routes.orders import router as orders_router
from app.core.logging_config import clear_log_context, set_log_context, setup_logging
from ddtrace import patch_all
from ddtrace.contrib.asgi import TraceMiddleware

patch_all()
setup_logging()

app = FastAPI(title="OS Service", version="0.1.0")
app.add_middleware(TraceMiddleware)
app.include_router(orders_router)


@app.middleware("http")
async def request_context_middleware(request, call_next):
    correlation_id = request.headers.get("x-correlation-id", str(uuid4()))
    set_log_context(
        correlation_id=correlation_id,
        request_method=request.method,
        request_path=request.url.path,
    )
    start = perf_counter()
    try:
        response = await call_next(request)
        duration_ms = round((perf_counter() - start) * 1000, 2)
        set_log_context(request_status=response.status_code, request_duration_ms=duration_ms)
        response.headers["x-correlation-id"] = correlation_id
        return response
    finally:
        clear_log_context()


@app.get("/health", tags=["Health"])
def health():
    return {"status": "healthy"}
