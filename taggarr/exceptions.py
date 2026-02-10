"""Taggarr exception hierarchy."""

from __future__ import annotations


class TaggarrError(Exception):
    """Base exception for all Taggarr errors."""


class ConfigError(TaggarrError):
    """Invalid configuration or missing keys."""


class ApiError(TaggarrError):
    """Base for all Sonarr/Radarr API errors."""


class ApiTransientError(ApiError):
    """Retryable API errors: 5xx, timeouts, connection failures."""


class ApiPermanentError(ApiError):
    """Non-retryable API errors: 4xx, auth failures."""
