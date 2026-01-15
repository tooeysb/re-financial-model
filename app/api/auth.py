"""
Authentication API endpoints.
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import User, InviteToken, PasswordResetToken, RefreshToken
from app.auth.password import verify_password, hash_password
from app.auth.jwt import create_access_token, create_refresh_token, decode_token
from app.auth.tokens import generate_token, hash_token, verify_token_hash
from app.auth.dependencies import get_current_user
from app.services.email import get_email_service
from app.config import get_settings

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()


# === Pydantic Schemas ===

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class RegisterRequest(BaseModel):
    token: str
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: Optional[str] = None  # Can also be read from cookie


class UserResponse(BaseModel):
    id: str
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    role: str
    email_verified: bool

    class Config:
        from_attributes = True


# === Helper Functions ===

def set_auth_cookies(response: Response, access_token: str, refresh_token: str):
    """Set httpOnly cookies for tokens."""
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.app_env == "production",
        samesite="lax",
        max_age=settings.jwt_access_token_expire_minutes * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.app_env == "production",
        samesite="lax",
        max_age=settings.jwt_refresh_token_expire_days * 24 * 60 * 60,
    )


def clear_auth_cookies(response: Response):
    """Clear auth cookies."""
    response.delete_cookie(key="access_token")
    response.delete_cookie(key="refresh_token")


def user_to_dict(user: User) -> dict:
    """Convert user model to dict for response."""
    return {
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role": user.role.value,
        "email_verified": user.email_verified,
    }


# === Endpoints ===

@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Authenticate user and return JWT tokens.

    Sets httpOnly cookies for browser-based auth.
    """
    # Find user
    user = db.query(User).filter(
        User.email == request.email.lower(),
        User.is_deleted == False,
    ).first()

    if not user or not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    # Update last login
    user.last_login_at = datetime.utcnow()
    db.commit()

    # Create tokens
    token_data = {"sub": user.id, "email": user.email, "role": user.role.value}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    # Store refresh token hash in database
    refresh_token_record = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(refresh_token),
        expires_at=datetime.utcnow() + timedelta(days=settings.jwt_refresh_token_expire_days),
    )
    db.add(refresh_token_record)
    db.commit()

    # Set cookies
    set_auth_cookies(response, access_token, refresh_token)

    return LoginResponse(
        access_token=access_token,
        user=user_to_dict(user),
    )


@router.post("/register")
async def register(
    request: RegisterRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Complete user registration using an invite token.
    """
    # Find and validate invite token
    invite = db.query(InviteToken).filter(
        InviteToken.token == request.token,
        InviteToken.is_deleted == False,
    ).first()

    if not invite:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired invite token",
        )

    if invite.used_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invite token has already been used",
        )

    if invite.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invite token has expired",
        )

    # Get the user associated with the invite
    user = db.query(User).filter(User.id == invite.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found",
        )

    # Update user
    user.hashed_password = hash_password(request.password)
    user.first_name = request.first_name
    user.last_name = request.last_name
    user.email_verified = True
    user.password_changed_at = datetime.utcnow()

    # Mark invite as used
    invite.used_at = datetime.utcnow()

    db.commit()

    # Send welcome email
    email_service = get_email_service()
    email_service.send_welcome_email(user.email, user.first_name)

    # Auto-login: create tokens
    token_data = {"sub": user.id, "email": user.email, "role": user.role.value}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    # Store refresh token
    refresh_token_record = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(refresh_token),
        expires_at=datetime.utcnow() + timedelta(days=settings.jwt_refresh_token_expire_days),
    )
    db.add(refresh_token_record)
    db.commit()

    set_auth_cookies(response, access_token, refresh_token)

    return {
        "message": "Registration successful",
        "access_token": access_token,
        "user": user_to_dict(user),
    }


@router.post("/forgot-password")
async def forgot_password(
    request: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    """
    Request a password reset email.

    Always returns success to prevent email enumeration.
    """
    user = db.query(User).filter(
        User.email == request.email.lower(),
        User.is_deleted == False,
        User.is_active == True,
    ).first()

    if user and user.hashed_password:  # Only for users who have completed registration
        # Generate reset token
        token = generate_token()

        # Create token record
        reset_token = PasswordResetToken(
            user_id=user.id,
            token=token,
            expires_at=datetime.utcnow() + timedelta(hours=settings.password_reset_token_expire_hours),
        )
        db.add(reset_token)
        db.commit()

        # Send email
        email_service = get_email_service()
        email_service.send_password_reset_email(user.email, token)

    # Always return success to prevent email enumeration
    return {"message": "If an account exists with that email, a password reset link has been sent."}


@router.post("/reset-password")
async def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    """
    Reset password using a reset token.
    """
    # Find and validate reset token
    reset_token = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == request.token,
        PasswordResetToken.is_deleted == False,
    ).first()

    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    if reset_token.used_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has already been used",
        )

    if reset_token.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired",
        )

    # Get user
    user = db.query(User).filter(User.id == reset_token.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found",
        )

    # Update password
    user.hashed_password = hash_password(request.password)
    user.password_changed_at = datetime.utcnow()

    # Mark token as used
    reset_token.used_at = datetime.utcnow()

    # Revoke all refresh tokens (log out all sessions)
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user.id,
        RefreshToken.revoked_at == None,
    ).update({"revoked_at": datetime.utcnow()})

    db.commit()

    return {"message": "Password has been reset successfully"}


@router.post("/refresh")
async def refresh_tokens(
    request: Request,
    response: Response,
    body: RefreshRequest = None,
    db: Session = Depends(get_db),
):
    """
    Refresh access token using refresh token.

    Accepts refresh token from body or cookie.
    """
    # Get refresh token from body or cookie
    refresh_token = None
    if body and body.refresh_token:
        refresh_token = body.refresh_token
    else:
        refresh_token = request.cookies.get("refresh_token")

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required",
        )

    # Decode token
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    user_id = payload.get("sub")
    token_hash = hash_token(refresh_token)

    # Find token in database
    stored_token = db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id,
        RefreshToken.token_hash == token_hash,
        RefreshToken.revoked_at == None,
        RefreshToken.is_deleted == False,
    ).first()

    if not stored_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found or revoked",
        )

    if stored_token.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired",
        )

    # Get user
    user = db.query(User).filter(
        User.id == user_id,
        User.is_deleted == False,
        User.is_active == True,
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    # Revoke old refresh token
    stored_token.revoked_at = datetime.utcnow()

    # Create new tokens
    token_data = {"sub": user.id, "email": user.email, "role": user.role.value}
    new_access_token = create_access_token(token_data)
    new_refresh_token = create_refresh_token(token_data)

    # Store new refresh token
    new_refresh_token_record = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(new_refresh_token),
        expires_at=datetime.utcnow() + timedelta(days=settings.jwt_refresh_token_expire_days),
    )
    db.add(new_refresh_token_record)
    db.commit()

    set_auth_cookies(response, new_access_token, new_refresh_token)

    return {
        "access_token": new_access_token,
        "token_type": "bearer",
    }


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Log out user by revoking refresh token and clearing cookies.
    """
    # Get refresh token from cookie
    refresh_token = request.cookies.get("refresh_token")

    if refresh_token:
        token_hash = hash_token(refresh_token)
        # Revoke the refresh token
        db.query(RefreshToken).filter(
            RefreshToken.user_id == current_user.id,
            RefreshToken.token_hash == token_hash,
        ).update({"revoked_at": datetime.utcnow()})
        db.commit()

    # Clear cookies
    clear_auth_cookies(response)

    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Get current user information.
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        role=current_user.role.value,
        email_verified=current_user.email_verified,
    )
