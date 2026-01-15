"""
Authentication and authorization module.
"""

from app.auth.password import verify_password, hash_password
from app.auth.jwt import create_access_token, create_refresh_token, decode_token
from app.auth.tokens import generate_token, hash_token, verify_token_hash
from app.auth.dependencies import (
    get_current_user,
    get_current_user_optional,
    require_admin,
)

__all__ = [
    "verify_password",
    "hash_password",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "generate_token",
    "hash_token",
    "verify_token_hash",
    "get_current_user",
    "get_current_user_optional",
    "require_admin",
]
