"""WebSocket endpoints for taggarr."""

import asyncio
import json
import logging
from collections import deque
from datetime import datetime, timezone
from typing import Set

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger("taggarr")

# In-memory ring buffer for recent log entries
MAX_LOG_BUFFER_SIZE = 1000
log_buffer: deque[dict] = deque(maxlen=MAX_LOG_BUFFER_SIZE)

# Connected WebSocket clients
connected_clients: Set[WebSocket] = set()


class WebSocketLogHandler(logging.Handler):
    """Custom logging handler that broadcasts logs to WebSocket clients."""

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record to all connected WebSocket clients.

        Args:
            record: The log record to emit.
        """
        try:
            log_entry = self.format_log_entry(record)
            log_buffer.append(log_entry)

            # Broadcast to all connected clients
            if connected_clients:
                message = json.dumps(log_entry)
                asyncio.create_task(self.broadcast(message))
        except Exception:
            # Don't raise in logging handler
            pass

    def format_log_entry(self, record: logging.LogRecord) -> dict:
        """Format a log record as a dictionary.

        Args:
            record: The log record to format.

        Returns:
            Dictionary with log entry data.
        """
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "funcName": record.funcName,
            "lineno": record.lineno,
        }

    async def broadcast(self, message: str) -> None:
        """Broadcast a message to all connected clients.

        Args:
            message: The JSON message to broadcast.
        """
        disconnected = set()
        for client in connected_clients:
            try:
                await client.send_text(message)
            except Exception:
                disconnected.add(client)

        # Clean up disconnected clients
        connected_clients.difference_update(disconnected)


async def websocket_logs(websocket: WebSocket) -> None:
    """WebSocket endpoint for streaming logs.

    Args:
        websocket: The WebSocket connection.
    """
    await websocket.accept()
    connected_clients.add(websocket)

    try:
        # Send buffered logs on connect
        for entry in log_buffer:
            await websocket.send_text(json.dumps(entry))

        # Keep connection alive and wait for disconnect
        while True:
            try:
                # Wait for messages (primarily for ping/pong or close)
                await websocket.receive_text()
            except WebSocketDisconnect:
                break
    finally:
        connected_clients.discard(websocket)


def setup_websocket_logging() -> WebSocketLogHandler:
    """Set up the WebSocket logging handler.

    Returns:
        The created WebSocketLogHandler.
    """
    handler = WebSocketLogHandler()
    handler.setLevel(logging.INFO)
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )

    # Add handler to the taggarr logger
    taggarr_logger = logging.getLogger("taggarr")
    taggarr_logger.addHandler(handler)

    return handler


def get_recent_logs(limit: int = 100) -> list[dict]:
    """Get recent log entries from the buffer.

    Args:
        limit: Maximum number of entries to return.

    Returns:
        List of recent log entries, newest first.
    """
    entries = list(log_buffer)[-limit:]
    return list(reversed(entries))
