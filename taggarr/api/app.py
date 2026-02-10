"""FastAPI application factory for taggarr."""

from typing import Callable

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from taggarr.api.routes import (
    apikeys_router,
    auth_router,
    backups_router,
    commands_router,
    config_router,
    history_router,
    instances_router,
    logs_router,
    media_router,
    notifications_router,
    stats_router,
    tags_router,
)
from taggarr.api.websocket import setup_websocket_logging, websocket_logs


def create_app(base_url: str = "/", lifespan: Callable | None = None) -> FastAPI:
    """Create and configure FastAPI application.

    Args:
        base_url: Base URL prefix for all routes (for reverse proxy support).
        lifespan: Optional lifespan context manager for the application.

    Returns:
        Configured FastAPI application instance.
    """
    app = FastAPI(
        title="Taggarr",
        description="Media library audio dub tagging tool",
        root_path=base_url.rstrip("/") if base_url != "/" else "",
        lifespan=lifespan,
    )

    # CORS middleware for development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "ok"}

    @app.get("/")
    async def root() -> dict[str, str]:
        """Root endpoint."""
        return {"message": "Taggarr API"}

    # WebSocket endpoint for log streaming
    @app.websocket("/api/v1/ws/logs")
    async def ws_logs(websocket: WebSocket):
        """WebSocket endpoint for real-time log streaming."""
        await websocket_logs(websocket)

    # Set up WebSocket logging handler
    setup_websocket_logging()

    # Include routers
    app.include_router(auth_router)
    app.include_router(apikeys_router)
    app.include_router(backups_router)
    app.include_router(commands_router)
    app.include_router(config_router)
    app.include_router(history_router)
    app.include_router(instances_router)
    app.include_router(logs_router)
    app.include_router(media_router)
    app.include_router(notifications_router)
    app.include_router(stats_router)
    app.include_router(tags_router)

    return app
