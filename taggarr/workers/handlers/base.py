"""Base handler interface for command execution."""

from abc import ABC, abstractmethod
from typing import Any, Callable

from sqlalchemy.orm import Session


class BaseHandler(ABC):
    """Base class for command handlers."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        """Initialize handler with session factory.

        Args:
            session_factory: Callable that returns a database session.
        """
        self._session_factory = session_factory

    @abstractmethod
    async def execute(self, **kwargs: Any) -> None:
        """Execute the command with given parameters.

        Args:
            **kwargs: Command-specific parameters.

        Raises:
            NotImplementedError: Must be implemented by subclasses.
        """
        raise NotImplementedError
