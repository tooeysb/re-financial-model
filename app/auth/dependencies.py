"""
FastAPI dependencies for authentication and authorization.
"""

from typing import Optional

from fastapi import Depends, HTTPException, status, Request, Cookie
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import User, UserRole
from app.auth.jwt import decode_token


def get_token_from_request(request: Request) -> Optional[str]:
    """
    Extract JWT token from request.

    Checks in order:
    1. Authorization header (Bearer token)
    2. access_token cookie

    Returns:
        Token string if found, None otherwise
    """
    # Check Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:]  # Remove "Bearer " prefix

    # Check cookie
    token = request.cookies.get("access_token")
    return token


async def get_current_user_optional(
    request: Request,
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    Get the current user if authenticated, None otherwise.

    Use this for routes that work both with and without authentication.
    """
    token = get_token_from_request(request)
    if not token:
        return None

    payload = decode_token(token)
    if not payload:
        return None

    # Verify token type
    if payload.get("type") != "access":
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    user = db.query(User).filter(
        User.id == user_id,
        User.is_deleted == False,
        User.is_active == True,
    ).first()

    return user


async def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """
    Get the current authenticated user.

    Raises HTTPException 401 if not authenticated.
    """
    user = await get_current_user_optional(request, db)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Require the current user to be an admin.

    Raises HTTPException 403 if user is not an admin.
    """
    if current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    return current_user
