"""Authentication package for taggarr."""

from taggarr.auth.apikey import generate_api_key, hash_api_key, verify_api_key
from taggarr.auth.password import hash_password, verify_password
from taggarr.auth.session import (
    create_session_token,
    get_session_expiry,
    is_session_expired,
)

__all__ = [
    "generate_api_key",
    "hash_api_key",
    "verify_api_key",
    "hash_password",
    "verify_password",
    "create_session_token",
    "get_session_expiry",
    "is_session_expired",
]
