"""FastAPI application factory for taggarr."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def create_app(base_url: str = "/") -> FastAPI:
    """Create and configure FastAPI application.

    Args:
        base_url: Base URL prefix for all routes (for reverse proxy support).

    Returns:
        Configured FastAPI application instance.
    """
    app = FastAPI(
        title="Taggarr",
        description="Media library audio dub tagging tool",
        root_path=base_url.rstrip("/") if base_url != "/" else "",
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

    return app
