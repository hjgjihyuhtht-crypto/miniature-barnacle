"""NEXUS AI FastAPI application entrypoint."""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.auth import sanitize_for_log
from backend.config import get_settings
from backend.database import close_db, init_db
from backend.memory.memory_manager import reset_memory_manager
from backend.routes import audio, chat, conversations, health, memory, models, providers, router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("nexus")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    settings.ensure_dirs()
    await init_db(settings)
    reset_memory_manager()
    logger.info("NEXUS AI backend started (db=%s)", settings.db_path)
    yield
    await close_db()
    logger.info("NEXUS AI backend stopped")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="NEXUS AI",
        version="1.0.0",
        description="Personal multi-model AI orchestrator",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Simple in-memory rate limit
    hits: dict[str, list[float]] = {}

    @app.middleware("http")
    async def security_middleware(request: Request, call_next):
        # Request size guard for non-streaming uploads (best-effort)
        cl = request.headers.get("content-length")
        if cl and int(cl) > settings.max_request_bytes:
            return JSONResponse({"detail": "Request too large"}, status_code=413)

        client = request.client.host if request.client else "unknown"
        now = time.time()
        window = hits.setdefault(client, [])
        hits[client] = [t for t in window if now - t < 60]
        if len(hits[client]) >= settings.rate_limit_per_minute:
            return JSONResponse({"detail": "Rate limit exceeded"}, status_code=429)
        hits[client].append(now)

        # Never log secrets
        auth = request.headers.get("authorization")
        if auth:
            logger.debug("auth=%s path=%s", sanitize_for_log(auth), request.url.path)

        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        return response

    app.include_router(health.router)
    app.include_router(models.router)
    app.include_router(providers.router)
    app.include_router(router.router)
    app.include_router(chat.router)
    app.include_router(memory.router)
    app.include_router(audio.router)
    app.include_router(conversations.router)

    return app


app = create_app()
