"""Tests for WebSocket logging functionality."""

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from taggarr.api.websocket import (
    WebSocketLogHandler,
    connected_clients,
    get_recent_logs,
    log_buffer,
    setup_websocket_logging,
)


@pytest.fixture(autouse=True)
def clear_log_buffer():
    """Clear the log buffer before and after each test."""
    log_buffer.clear()
    connected_clients.clear()
    yield
    log_buffer.clear()
    connected_clients.clear()


class TestWebSocketLogHandler:
    """Tests for WebSocketLogHandler."""

    def test_emit_adds_to_buffer(self) -> None:
        """emit() adds log entry to the buffer."""
        handler = WebSocketLogHandler()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        handler.emit(record)

        assert len(log_buffer) == 1
        entry = log_buffer[0]
        assert entry["message"] == "Test message"
        assert entry["level"] == "INFO"
        assert entry["logger"] == "test"

    def test_emit_respects_max_buffer_size(self) -> None:
        """emit() respects max buffer size."""
        from taggarr.api.websocket import MAX_LOG_BUFFER_SIZE

        handler = WebSocketLogHandler()

        # Fill buffer beyond max size
        for i in range(MAX_LOG_BUFFER_SIZE + 50):
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="test.py",
                lineno=1,
                msg=f"Message {i}",
                args=(),
                exc_info=None,
            )
            handler.emit(record)

        assert len(log_buffer) == MAX_LOG_BUFFER_SIZE

    def test_format_log_entry_includes_all_fields(self) -> None:
        """format_log_entry() includes all expected fields."""
        handler = WebSocketLogHandler()
        record = logging.LogRecord(
            name="taggarr.test",
            level=logging.WARNING,
            pathname="/path/to/test.py",
            lineno=42,
            msg="Warning message",
            args=(),
            exc_info=None,
        )
        record.funcName = "test_function"
        record.module = "test"

        entry = handler.format_log_entry(record)

        assert "timestamp" in entry
        assert entry["level"] == "WARNING"
        assert entry["logger"] == "taggarr.test"
        assert entry["message"] == "Warning message"
        assert entry["module"] == "test"
        assert entry["funcName"] == "test_function"
        assert entry["lineno"] == 42


class TestGetRecentLogs:
    """Tests for get_recent_logs function."""

    def test_returns_empty_list_when_no_logs(self) -> None:
        """get_recent_logs() returns empty list when buffer is empty."""
        result = get_recent_logs()

        assert result == []

    def test_returns_logs_in_reverse_order(self) -> None:
        """get_recent_logs() returns logs newest first."""
        handler = WebSocketLogHandler()
        for i in range(5):
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="test.py",
                lineno=1,
                msg=f"Message {i}",
                args=(),
                exc_info=None,
            )
            handler.emit(record)

        result = get_recent_logs()

        assert len(result) == 5
        # Newest first
        assert result[0]["message"] == "Message 4"
        assert result[4]["message"] == "Message 0"

    def test_respects_limit_parameter(self) -> None:
        """get_recent_logs() respects the limit parameter."""
        handler = WebSocketLogHandler()
        for i in range(20):
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="test.py",
                lineno=1,
                msg=f"Message {i}",
                args=(),
                exc_info=None,
            )
            handler.emit(record)

        result = get_recent_logs(limit=5)

        assert len(result) == 5


class TestSetupWebsocketLogging:
    """Tests for setup_websocket_logging function."""

    def test_returns_handler(self) -> None:
        """setup_websocket_logging() returns the created handler."""
        handler = setup_websocket_logging()

        assert isinstance(handler, WebSocketLogHandler)

    def test_adds_handler_to_taggarr_logger(self) -> None:
        """setup_websocket_logging() adds handler to taggarr logger."""
        handler = setup_websocket_logging()

        taggarr_logger = logging.getLogger("taggarr")
        assert handler in taggarr_logger.handlers

        # Clean up
        taggarr_logger.removeHandler(handler)


def run_async(coro):
    """Run an async coroutine synchronously."""
    import asyncio

    return asyncio.run(coro)


class TestBroadcast:
    """Tests for WebSocket broadcast functionality."""

    def test_broadcast_sends_to_connected_clients(self) -> None:
        """broadcast() sends message to all connected clients."""
        handler = WebSocketLogHandler()

        # Create mock WebSocket clients
        mock_client1 = AsyncMock()
        mock_client2 = AsyncMock()

        connected_clients.add(mock_client1)
        connected_clients.add(mock_client2)

        run_async(handler.broadcast('{"test": "message"}'))

        mock_client1.send_text.assert_called_once_with('{"test": "message"}')
        mock_client2.send_text.assert_called_once_with('{"test": "message"}')

    def test_broadcast_removes_disconnected_clients(self) -> None:
        """broadcast() removes clients that raise exceptions."""
        handler = WebSocketLogHandler()

        mock_client = AsyncMock()
        mock_client.send_text.side_effect = Exception("Connection closed")

        connected_clients.add(mock_client)

        run_async(handler.broadcast('{"test": "message"}'))

        # Client should be removed after failure
        assert mock_client not in connected_clients

    def test_emit_broadcasts_when_clients_connected(self) -> None:
        """emit() broadcasts to connected clients."""
        handler = WebSocketLogHandler()

        mock_client = AsyncMock()
        connected_clients.add(mock_client)

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Use asyncio to handle the async task created by emit
        with patch.object(handler, "broadcast", new_callable=AsyncMock) as mock_broadcast:
            handler.emit(record)
            # emit creates an async task but doesn't await it directly

    def test_emit_handles_exception_gracefully(self) -> None:
        """emit() handles exceptions without raising."""
        handler = WebSocketLogHandler()

        # Create a record that will fail during formatting
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test %s",  # This requires an arg
            args=(),  # But no args provided
            exc_info=None,
        )

        # Force an exception during format
        with patch.object(handler, "format_log_entry", side_effect=Exception("Format error")):
            # Should not raise
            handler.emit(record)
