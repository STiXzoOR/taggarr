"""Command queue processor for taggarr."""

import asyncio
import json
import logging
from datetime import datetime
from typing import Callable

from sqlalchemy.orm import Session

from taggarr.db import Command
from taggarr.workers.handlers import HANDLERS

logger = logging.getLogger("taggarr")


class CommandProcessor:
    """Processes queued commands from the database."""

    def __init__(self, db_session_factory: Callable[[], Session]) -> None:
        """Initialize with a session factory callable.

        Args:
            db_session_factory: A callable that returns a database session.
        """
        self._session_factory = db_session_factory
        self._running = False

    async def start(self, poll_interval: float = 5.0) -> None:
        """Start processing commands.

        Args:
            poll_interval: Time in seconds between polling for new commands.
        """
        self._running = True
        while self._running:
            await self._process_next()
            await asyncio.sleep(poll_interval)

    def stop(self) -> None:
        """Stop the processor."""
        self._running = False

    async def _process_next(self) -> None:
        """Process the next queued command."""
        with self._session_factory() as db:
            command = (
                db.query(Command)
                .filter(Command.status == "Queued")
                .order_by(Command.queued_at)
                .first()
            )

            if not command:
                return

            # Mark as started
            command.status = "Started"
            command.started_at = datetime.utcnow()
            db.commit()

            try:
                # Execute command (dispatch to handler)
                await self._execute(command.name, command.body)

                command.status = "Completed"
                command.ended_at = datetime.utcnow()
            except Exception as e:
                command.status = "Failed"
                command.ended_at = datetime.utcnow()
                command.exception = str(e)

            db.commit()

    async def _execute(self, name: str, body: str | None) -> None:
        """Execute a command by name.

        Args:
            name: The command name to execute.
            body: Optional JSON body containing command parameters.

        Raises:
            ValueError: If the command name is not recognized.
        """
        handler_class = HANDLERS.get(name)
        if not handler_class:
            logger.warning(f"Unknown command: {name}")
            raise ValueError(f"Unknown command: {name}")

        params = json.loads(body) if body else {}
        handler = handler_class(self._session_factory)
        await handler.execute(**params)
