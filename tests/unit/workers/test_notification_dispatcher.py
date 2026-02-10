"""Tests for taggarr.workers.notification_dispatcher module."""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock

import pytest
from sqlalchemy.orm import sessionmaker

from taggarr.db.database import create_engine
from taggarr.db.models import Base, Notification, NotificationStatus
from taggarr.workers.notification_dispatcher import (
    NotificationDispatcher,
    NotificationEvent,
)


@pytest.fixture
def db_engine(tmp_path: Path):
    """Create a temporary in-memory database engine."""
    db_path = tmp_path / "test.db"
    url = f"sqlite:///{db_path}"
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session_factory(db_engine):
    """Create a session factory for the test database."""
    return sessionmaker(bind=db_engine)


@pytest.fixture
def dispatcher(session_factory):
    """Create a NotificationDispatcher instance."""
    return NotificationDispatcher(session_factory)


def _create_notification(
    session,
    name: str = "Test Notification",
    implementation: str = "email",
    on_wrong_dub_detected: int = 0,
    on_original_missing: int = 0,
    on_health_issue: int = 0,
    include_health_warnings: int = 0,
) -> Notification:
    """Helper to create a notification."""
    notification = Notification(
        name=name,
        implementation=implementation,
        settings="{}",
        on_wrong_dub_detected=on_wrong_dub_detected,
        on_original_missing=on_original_missing,
        on_health_issue=on_health_issue,
        include_health_warnings=include_health_warnings,
    )
    session.add(notification)
    session.commit()
    return notification


class TestNotificationDispatcherInit:
    """Tests for NotificationDispatcher initialization."""

    def test_init_stores_session_factory(self, session_factory) -> None:
        """NotificationDispatcher should store the session factory."""
        dispatcher = NotificationDispatcher(session_factory)
        assert dispatcher._session_factory is session_factory


class TestDispatchFindsApplicableNotifications:
    """Tests for dispatcher finding applicable notifications."""

    def test_dispatch_finds_applicable_notifications(
        self, dispatcher, session_factory
    ) -> None:
        """Dispatcher should find notifications that match the event type."""
        with session_factory() as session:
            # Create a notification that listens for wrong_dub events
            _create_notification(
                session,
                name="Wrong Dub Notifier",
                on_wrong_dub_detected=1,
            )

        # Track which notifications were sent
        sent_notifications = []
        original_send = dispatcher._send

        def tracking_send(notification, title, message):
            sent_notifications.append(notification.name)
            return original_send(notification, title, message)

        dispatcher._send = tracking_send

        # Dispatch a wrong_dub event
        dispatcher.dispatch(
            NotificationEvent.WRONG_DUB,
            "Wrong Dub Detected",
            "Show X has wrong dub",
        )

        assert "Wrong Dub Notifier" in sent_notifications


class TestDispatchFiltersByEventType:
    """Tests for dispatcher filtering by event type."""

    def test_dispatch_filters_by_event_type(
        self, dispatcher, session_factory
    ) -> None:
        """Dispatcher should only send to notifications matching the event."""
        with session_factory() as session:
            # Create notifications for different event types
            _create_notification(
                session,
                name="Wrong Dub Only",
                on_wrong_dub_detected=1,
                on_original_missing=0,
            )
            _create_notification(
                session,
                name="Original Missing Only",
                on_wrong_dub_detected=0,
                on_original_missing=1,
            )

        sent_notifications = []
        original_send = dispatcher._send

        def tracking_send(notification, title, message):
            sent_notifications.append(notification.name)
            return original_send(notification, title, message)

        dispatcher._send = tracking_send

        # Dispatch an original_missing event
        dispatcher.dispatch(
            NotificationEvent.ORIGINAL_MISSING,
            "Original Missing",
            "Show Y has no original audio",
        )

        # Only the original_missing notification should be sent
        assert "Original Missing Only" in sent_notifications
        assert "Wrong Dub Only" not in sent_notifications

    def test_dispatch_filters_health_warning_events(
        self, dispatcher, session_factory
    ) -> None:
        """Dispatcher should filter health warning events correctly."""
        with session_factory() as session:
            _create_notification(
                session,
                name="Health Notifier",
                on_health_issue=1,
                include_health_warnings=1,
            )
            _create_notification(
                session,
                name="No Health",
                on_health_issue=0,
                include_health_warnings=0,
            )

        sent_notifications = []
        original_send = dispatcher._send

        def tracking_send(notification, title, message):
            sent_notifications.append(notification.name)
            return original_send(notification, title, message)

        dispatcher._send = tracking_send

        dispatcher.dispatch(
            NotificationEvent.HEALTH_WARNING,
            "Health Check",
            "Instance unreachable",
        )

        assert "Health Notifier" in sent_notifications
        assert "No Health" not in sent_notifications


class TestDispatchIgnoresNotificationsNotMatchingEvent:
    """Tests for dispatcher ignoring non-matching notifications."""

    def test_dispatch_ignores_notifications_not_matching_event(
        self, dispatcher, session_factory
    ) -> None:
        """Dispatcher should not send to notifications that don't match."""
        with session_factory() as session:
            # Create a notification that does NOT listen for wrong_dub
            _create_notification(
                session,
                name="Other Notifier",
                on_wrong_dub_detected=0,
                on_original_missing=1,
            )

        sent_notifications = []
        original_send = dispatcher._send

        def tracking_send(notification, title, message):
            sent_notifications.append(notification.name)
            return original_send(notification, title, message)

        dispatcher._send = tracking_send

        # Dispatch a wrong_dub event
        dispatcher.dispatch(
            NotificationEvent.WRONG_DUB,
            "Wrong Dub",
            "Message",
        )

        # The notification should not be sent
        assert "Other Notifier" not in sent_notifications


class TestDispatchUpdatesLastSentTimestamp:
    """Tests for dispatcher updating last_sent_at timestamp."""

    def test_dispatch_updates_last_sent_timestamp(
        self, dispatcher, session_factory
    ) -> None:
        """Dispatcher should update last_sent_at after sending."""
        with session_factory() as session:
            notification = _create_notification(
                session,
                name="Timestamp Test",
                on_wrong_dub_detected=1,
            )
            notification_id = notification.id
            # Create an existing status record
            status = NotificationStatus(
                notification_id=notification_id,
                last_sent_at=datetime(2020, 1, 1),
            )
            session.add(status)
            session.commit()

        before = datetime.now(timezone.utc)
        dispatcher.dispatch(
            NotificationEvent.WRONG_DUB,
            "Test",
            "Message",
        )
        after = datetime.now(timezone.utc)

        with session_factory() as session:
            status = (
                session.query(NotificationStatus)
                .filter(NotificationStatus.notification_id == notification_id)
                .first()
            )
            assert status is not None
            assert status.last_sent_at is not None
            # The timestamp should be updated to a recent time
            assert before.replace(tzinfo=None) <= status.last_sent_at
            assert status.last_sent_at <= after.replace(tzinfo=None)


class TestDispatchCreatesStatusIfMissing:
    """Tests for dispatcher creating status record if missing."""

    def test_dispatch_creates_status_if_missing(
        self, dispatcher, session_factory
    ) -> None:
        """Dispatcher should create NotificationStatus if it doesn't exist."""
        with session_factory() as session:
            notification = _create_notification(
                session,
                name="New Status Test",
                on_wrong_dub_detected=1,
            )
            notification_id = notification.id
            # No status record exists

        before = datetime.now(timezone.utc)
        dispatcher.dispatch(
            NotificationEvent.WRONG_DUB,
            "Test",
            "Message",
        )
        after = datetime.now(timezone.utc)

        with session_factory() as session:
            status = (
                session.query(NotificationStatus)
                .filter(NotificationStatus.notification_id == notification_id)
                .first()
            )
            assert status is not None
            assert status.last_sent_at is not None
            assert before.replace(tzinfo=None) <= status.last_sent_at
            assert status.last_sent_at <= after.replace(tzinfo=None)


class TestNotificationEventEnum:
    """Tests for NotificationEvent enum values."""

    def test_event_values(self) -> None:
        """NotificationEvent should have expected values."""
        assert NotificationEvent.WRONG_DUB.value == "wrong_dub"
        assert NotificationEvent.ORIGINAL_MISSING.value == "original_missing"
        assert NotificationEvent.HEALTH_WARNING.value == "health_warning"


class TestSendMethod:
    """Tests for NotificationDispatcher._send method."""

    def test_send_success_logs_info(self, dispatcher, caplog) -> None:
        """_send logs success message when provider.send succeeds."""
        import logging
        caplog.set_level(logging.INFO)

        notification = MagicMock(implementation="webhook", settings="{}")

        mock_provider = MagicMock()
        mock_provider.return_value.send = AsyncMock()

        with patch("taggarr.workers.notification_dispatcher.get_provider", return_value=mock_provider):
            dispatcher._send(notification, "Test Title", "Test Message")

        assert "Notification sent via webhook" in caplog.text

    def test_send_generic_exception_logs_error(self, dispatcher, caplog) -> None:
        """_send logs error on generic exception."""
        import logging
        caplog.set_level(logging.ERROR)

        notification = MagicMock(implementation="webhook", settings="{}")

        mock_provider = MagicMock()
        mock_provider.return_value.send = AsyncMock(side_effect=RuntimeError("Connection failed"))

        with patch("taggarr.workers.notification_dispatcher.get_provider", return_value=mock_provider):
            dispatcher._send(notification, "Test Title", "Test Message")

        assert "Failed to send notification via webhook" in caplog.text

    def test_send_value_error_logs_provider_error(self, dispatcher, caplog) -> None:
        """_send logs provider error on ValueError."""
        import logging
        caplog.set_level(logging.ERROR)

        notification = MagicMock(implementation="webhook", settings="{}")

        mock_provider = MagicMock()
        mock_provider.return_value.send = AsyncMock(side_effect=ValueError("Bad config"))

        with patch("taggarr.workers.notification_dispatcher.get_provider", return_value=mock_provider):
            dispatcher._send(notification, "Test Title", "Test Message")

        assert "Notification provider error" in caplog.text
