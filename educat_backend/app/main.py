"""
EduCat AI — FastAPI Application Entry Point
Production-grade setup: CORS, rate limiting, structured logging,
Sentry error tracking, lifespan context manager.
"""
import time
import uuid
from contextlib import asynccontextmanager

import sentry_sdk
import structlog
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import settings
from app.core.database import get_supabase, close_supabase
from app.core.firebase import get_firebase_app
from app.core.redis_client import get_redis, close_redis

# ── Routers ───────────────────────────────────────────────────────
from app.routers import (
    auth,
    chat,
    users,
    content,
    subscriptions,
    admin,
    teacher,
    webhooks,
    school,
)

log = structlog.get_logger()

# ── Rate Limiter ──────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])


# ── Lifespan ──────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup + shutdown lifecycle."""
    log.info("starting_up", version=settings.APP_VERSION, env=settings.ENVIRONMENT)

    # Initialize connections
    await get_supabase()
    await get_redis()
    get_firebase_app()

    # Initialize Sentry in production
    if settings.SENTRY_DSN and settings.is_production:
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            traces_sample_rate=0.1,
            environment=settings.ENVIRONMENT,
        )
        log.info("sentry_initialized")

    log.info("startup_complete")
    yield

    # Shutdown
    log.info("shutting_down")
    await close_supabase()
    await close_redis()
    log.info("shutdown_complete")


# ── App Factory ───────────────────────────────────────────────────
def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="EduCat AI — Advanced Educational AI Platform Backend",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # ── Rate Limiter ──────────────────────────────────────────────
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # ── CORS ──────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-RateLimit-Limit", "X-RateLimit-Remaining"],
    )

    # ── GZip ──────────────────────────────────────────────────────
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # ── Request ID + Timing Middleware ────────────────────────────
    @app.middleware("http")
    async def request_middleware(request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id
        start = time.perf_counter()

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        try:
            response = await call_next(request)
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration_ms}ms"

            log.info("request_completed",
                     status_code=response.status_code,
                     duration_ms=duration_ms)
            return response
        except Exception as e:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            log.error("request_failed", error=str(e), duration_ms=duration_ms)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"success": False, "error": "Internal server error",
                         "request_id": request_id},
            )

    # ── Register Routers ──────────────────────────────────────────
    prefix = settings.API_PREFIX
    app.include_router(auth,          prefix=f"{prefix}/auth",          tags=["Auth"])
    app.include_router(chat,          prefix=f"{prefix}/chat",          tags=["Chat & AI"])
    app.include_router(users,         prefix=f"{prefix}/users",         tags=["Users"])
    app.include_router(content,       prefix=f"{prefix}/content",       tags=["Content"])
    app.include_router(subscriptions, prefix=f"{prefix}/subscriptions", tags=["Subscriptions"])
    app.include_router(teacher,       prefix=f"{prefix}/teacher",       tags=["Teacher"])
    app.include_router(admin,         prefix=f"{prefix}/admin",         tags=["Admin"])
    app.include_router(webhooks,      prefix=f"{prefix}/webhooks",      tags=["Webhooks"])
    app.include_router(school,        prefix=f"{prefix}/school",        tags=["School Dashboard"])

    # ── Health Check ──────────────────────────────────────────────
    @app.get("/health", tags=["Health"])
    async def health_check():
        try:
            redis = await get_redis()
            await redis.ping()
            redis_ok = True
        except Exception:
            redis_ok = False

        return {
            "status": "ok" if redis_ok else "degraded",
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "services": {
                "redis": "ok" if redis_ok else "error",
                "database": "ok",
            },
        }

    @app.get("/", tags=["Health"])
    async def root():
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs": "/docs" if not settings.is_production else "disabled",
        }

    return app


app = create_app()
