"""Web server for taggarr UI."""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI
from sqlalchemy.orm import sessionmaker

from taggarr.api.app import create_app
from taggarr.db import create_engine, init_db
from taggarr.workers.backup_scheduler import BackupScheduler
from taggarr.workers.command_processor import CommandProcessor
from taggarr.workers.scan_scheduler import ScanScheduler

logger = logging.getLogger("taggarr")


def _create_lifespan(engine, db_path: Path):
    """Create a lifespan context manager for the FastAPI app.

    Args:
        engine: SQLAlchemy database engine.
        db_path: Path to the SQLite database file.

    Returns:
        Async context manager for FastAPI lifespan.
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        """Manage application lifecycle including workers.

        Args:
            app: FastAPI application instance.

        Yields:
            None during application runtime.
        """
        # Store startup time and db path
        app.state.startup_time = datetime.now(timezone.utc)
        app.state.db_path = db_path

        # Create session factory for workers
        session_factory = sessionmaker(bind=engine)

        # Initialize workers
        workers = [
            CommandProcessor(session_factory),
            ScanScheduler(session_factory),
            BackupScheduler(session_factory),
        ]

        # Start worker tasks
        tasks = [asyncio.create_task(w.start()) for w in workers]

        logger.info("Starting CommandProcessor")
        logger.info("Starting ScanScheduler")
        logger.info("Starting BackupScheduler")

        try:
            yield
        finally:
            # Stop all workers
            logger.info("Stopping workers...")
            for w in workers:
                w.stop()

            # Wait for tasks to complete with timeout
            await asyncio.gather(*tasks, return_exceptions=True)
            logger.info("Workers stopped")

    return lifespan


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

    # Create lifespan context manager
    lifespan = _create_lifespan(engine, db_path)

    # Create FastAPI app with lifespan
    app = create_app(base_url=base_url, lifespan=lifespan)

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
