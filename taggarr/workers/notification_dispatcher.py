"""Notification dispatcher for taggarr."""

import asyncio
import json
import logging
from datetime import datetime, timezone
from enum import Enum

from taggarr.db import Notification, NotificationStatus
from taggarr.workers.providers import get_provider

logger = logging.getLogger("taggarr")


class NotificationEvent(Enum):
    """Event types that can trigger notifications."""

    WRONG_DUB = "wrong_dub"
    ORIGINAL_MISSING = "original_missing"
    HEALTH_WARNING = "health_warning"


class NotificationDispatcher:
    """Dispatches notifications to configured channels."""

    def __init__(self, db_session_factory):
        """Initialize the dispatcher with a session factory.

        Args:
            db_session_factory: A callable that returns a database session.
        """
        self._session_factory = db_session_factory

    def dispatch(self, event: NotificationEvent, title: str, message: str):
        """Dispatch notification to all applicable channels.

        Args:
            event: The type of notification event.
            title: The notification title.
            message: The notification message body.
        """
        with self._session_factory() as db:
            notifications = self._get_applicable_notifications(db, event)
            for notification in notifications:
                self._send(notification, title, message)
                self._update_status(db, notification.id)
            db.commit()

    def _get_applicable_notifications(self, db, event: NotificationEvent):
        """Get notifications that should receive this event.

        Args:
            db: The database session.
            event: The type of notification event.

        Returns:
            List of Notification objects that should receive this event.
        """
        query = db.query(Notification)

        if event == NotificationEvent.WRONG_DUB:
            query = query.filter(Notification.on_wrong_dub_detected == 1)
        elif event == NotificationEvent.ORIGINAL_MISSING:
            query = query.filter(Notification.on_original_missing == 1)
        elif event == NotificationEvent.HEALTH_WARNING:
            query = query.filter(Notification.on_health_issue == 1)
            query = query.filter(Notification.include_health_warnings == 1)

        return query.all()

    def _send(self, notification: Notification, title: str, message: str):
        """Send notification via provider.

        Args:
            notification: The notification configuration.
            title: The notification title.
            message: The notification message body.
        """
        try:
            provider_class = get_provider(notification.implementation)
            provider = provider_class()

            # Parse settings if stored as JSON string
            settings = notification.settings
            if isinstance(settings, str):
                settings = json.loads(settings)

            # Run the async send in a new event loop if needed
            asyncio.run(provider.send(title, message, settings))

            logger.info(
                f"Notification sent via {notification.implementation}: {title}"
            )
        except ValueError as e:
            logger.error(f"Notification provider error: {e}")
        except Exception as e:
            logger.error(
                f"Failed to send notification via {notification.implementation}: {e}"
            )

    def _update_status(self, db, notification_id: int):
        """Update last sent timestamp.

        Args:
            db: The database session.
            notification_id: The ID of the notification to update.
        """
        status = (
            db.query(NotificationStatus)
            .filter(NotificationStatus.notification_id == notification_id)
            .first()
        )

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if status:
            status.last_sent_at = now
        else:
            status = NotificationStatus(
                notification_id=notification_id,
                last_sent_at=now,
            )
            db.add(status)
