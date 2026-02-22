"""FastAPI application factory and entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from canarai import __version__
from canarai.config import get_settings
from canarai.db.engine import dispose_engine, init_db
from canarai.routers import config, feed, health, ingest, providers, results, sites, webhooks

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown."""
    # Startup
    settings = get_settings()
    logging.basicConfig(
        level=logging.DEBUG if settings.environment == "development" else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logger.info("Starting canar.ai API v%s in %s mode", __version__, settings.environment)

    # Reject insecure default secrets in production
    settings.validate_production()

    # Create tables (for SQLite dev mode; production uses Alembic migrations)
    if settings.environment == "development":
        await init_db()
        logger.info("Database tables created/verified")

    yield

    # Shutdown
    await dispose_engine()
    logger.info("canar.ai API shut down")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    # Disable interactive docs in production to reduce attack surface
    docs_url = "/docs" if settings.environment == "development" else None
    redoc_url = "/redoc" if settings.environment == "development" else None
    openapi_url = "/openapi.json" if settings.environment == "development" else None

    app = FastAPI(
        title="canar.ai API",
        description="AI Agent Prompt Injection Testing Backend",
        version=__version__,
        lifespan=lifespan,
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
    )

    # CORS middleware - credentials disabled since the script sends credentials: 'omit'
    origins = [o.strip() for o in settings.cors_origins.split(",")]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Middleware: rewrite text/plain to application/json for /v1/ingest
    # The canary script sends text/plain to avoid CORS preflight requests
    @app.middleware("http")
    async def rewrite_ingest_content_type(request: Request, call_next):
        if request.url.path == "/v1/ingest" and request.method == "POST":
            content_type = request.headers.get("content-type", "")
            if "text/plain" in content_type:
                new_headers = []
                for k, v in request.scope["headers"]:
                    if k == b"content-type":
                        new_headers.append((k, b"application/json"))
                    else:
                        new_headers.append((k, v))
                request.scope["headers"] = new_headers
        return await call_next(request)

    # Security headers middleware
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Cache-Control"] = "no-store"
        return response

    # Include routers
    app.include_router(health.router)
    app.include_router(ingest.router)
    app.include_router(config.router)
    app.include_router(sites.router)
    app.include_router(results.router)
    app.include_router(webhooks.router)
    app.include_router(feed.router)
    app.include_router(providers.router)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "canarai.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=(settings.environment == "development"),
    )
