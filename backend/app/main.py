import uuid

import sentry_sdk
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sentry_sdk.integrations.fastapi import FastApiIntegration

from app.api.v1.auth import router as auth_router
from app.api.v1.organization import router as organization_router
from app.core.config import get_settings
from app.core.logging import configure_logging, request_id_ctx

settings = get_settings()

configure_logging()

if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        integrations=[FastApiIntegration()],
    )

app = FastAPI(title="NeuronOS API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    """Every log line carries `request_id` (Blueprint §15) and the response echoes it back
    per the standard envelope's `meta.request_id` (API Spec §0.2)."""
    request_id = str(uuid.uuid4())
    token = request_id_ctx.set(request_id)
    try:
        response = await call_next(request)
    finally:
        request_id_ctx.reset(token)
    response.headers["X-Request-Id"] = request_id
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Routes raise `HTTPException(detail={"error": {"code": ..., "message": ...}})`
    (API Spec §0.3) — FastAPI's own default handler would otherwise nest that under a
    `"detail"` key instead of returning it as the top-level envelope this API documents,
    so it's overridden here rather than relied on as-is."""
    request_id = request_id_ctx.get()
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        content = {**exc.detail, "meta": {"request_id": request_id}}
    else:
        content = {
            "error": {"code": "internal_error", "message": str(exc.detail)},
            "meta": {"request_id": request_id},
        }
    return JSONResponse(status_code=exc.status_code, content=content)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = request_id_ctx.get()
    return JSONResponse(
        status_code=500,
        content={
            "error": {"code": "internal_error", "message": "An unexpected error occurred."},
            "meta": {"request_id": request_id},
        },
    )


app.include_router(auth_router, prefix="/api/v1")
app.include_router(organization_router, prefix="/api/v1")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
