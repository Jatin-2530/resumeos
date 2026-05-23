import os
import structlog
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.routes import resume, jd, generation, export_routes, validation, preview

settings = get_settings()
logger = structlog.get_logger()

# Rate limiter backed by Redis
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=os.getenv("REDIS_URL", "redis://localhost:6379"),
    default_limits=[f"{settings.rate_limit_requests_per_minute}/minute"],
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(settings.render_temp_dir, exist_ok=True)
    logger.info("ResumeOS API started", env=settings.python_env)
    yield
    logger.info("ResumeOS API shutting down")


app = FastAPI(
    title="ResumeOS API",
    description="Constraint-Aware Resume Intelligence Platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
)

# ── Middleware ────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(resume.router, prefix="/api/v1")
app.include_router(jd.router, prefix="/api/v1")
app.include_router(generation.router, prefix="/api/v1")
app.include_router(export_routes.router, prefix="/api/v1")
app.include_router(validation.router, prefix="/api/v1")
app.include_router(preview.router, prefix="/api/v1")


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok", "version": "1.0.0", "env": settings.python_env}


# ── Global error handler ──────────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception", path=str(request.url), error=str(exc))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )
