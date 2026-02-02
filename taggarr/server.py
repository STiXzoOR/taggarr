"""Web server for taggarr UI."""

from pathlib import Path

import uvicorn

from taggarr.api.app import create_app
from taggarr.db import create_engine, init_db


def create_server(
    host: str = "0.0.0.0",
    port: int = 8080,
    base_url: str = "/",
    db_path: Path | None = None,
):
    """Create and configure the server.

    Args:
        host: Host to bind to.
        port: Port to listen on.
        base_url: Base URL prefix for reverse proxy support.
        db_path: Path to SQLite database file.

    Returns:
        Configured FastAPI application instance.
    """
    # Set up database
    db_path = db_path or Path("./taggarr.db")
    engine = create_engine(f"sqlite:///{db_path}")
    init_db(engine)

    # Create FastAPI app
    app = create_app(base_url=base_url)

    # Store engine in app state for dependency injection
    app.state.db_engine = engine

    return app


def run_server(
    host: str = "0.0.0.0",
    port: int = 8080,
    base_url: str = "/",
    db_path: Path | None = None,
    reload: bool = False,
):
    """Run the web server.

    Args:
        host: Host to bind to.
        port: Port to listen on.
        base_url: Base URL prefix for reverse proxy support.
        db_path: Path to SQLite database file.
        reload: Enable auto-reload for development.
    """
    app = create_server(host, port, base_url, db_path)

    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=reload,
    )
