"""
Token generation and hashing utilities.

Used for invite tokens, password reset tokens, and refresh token storage.
"""

import secrets
import hashlib
from typing import Tuple


def generate_token(length: int = 32) -> str:
    """
    Generate a cryptographically secure random token.

    Args:
        length: Number of bytes (token will be 2x this in hex chars)

    Returns:
        Hex-encoded token string
    """
    return secrets.token_hex(length)


def hash_token(token: str) -> str:
    """
    Create a SHA-256 hash of a token for secure storage.

    Args:
        token: The plain token string

    Returns:
        Hex-encoded SHA-256 hash
    """
    return hashlib.sha256(token.encode()).hexdigest()


def verify_token_hash(token: str, token_hash: str) -> bool:
    """
    Verify a token against its stored hash.

    Args:
        token: The plain token to verify
        token_hash: The stored hash to compare against

    Returns:
        True if token matches hash, False otherwise
    """
    return secrets.compare_digest(hash_token(token), token_hash)


def generate_token_pair() -> Tuple[str, str]:
    """
    Generate a token and its hash.

    Returns:
        Tuple of (plain_token, token_hash)
    """
    token = generate_token()
    return token, hash_token(token)
