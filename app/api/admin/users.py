"""
Admin user management endpoints.
"""

from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import User, UserRole, InviteToken
from app.auth.dependencies import require_admin
from app.auth.tokens import generate_token
from app.services.email import get_email_service
from app.config import get_settings

router = APIRouter(prefix="/api/admin/users", tags=["admin"])
settings = get_settings()


# === Pydantic Schemas ===

class UserListItem(BaseModel):
    id: str
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    role: str
    is_active: bool
    email_verified: bool
    created_at: datetime
    last_login_at: Optional[datetime]

    class Config:
        from_attributes = True


class UserDetail(UserListItem):
    updated_at: datetime
    password_changed_at: Optional[datetime]


class InviteUserRequest(BaseModel):
    email: EmailStr
    role: str = "user"
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class UpdateUserRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class InviteResponse(BaseModel):
    message: str
    user_id: str
    email: str


# === Endpoints ===

@router.get("", response_model=List[UserListItem])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    include_deleted: bool = False,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    List all users (admin only).
    """
    query = db.query(User)

    if not include_deleted:
        query = query.filter(User.is_deleted == False)

    users = query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()

    return [
        UserListItem(
            id=u.id,
            email=u.email,
            first_name=u.first_name,
            last_name=u.last_name,
            role=u.role.value,
            is_active=u.is_active,
            email_verified=u.email_verified,
            created_at=u.created_at,
            last_login_at=u.last_login_at,
        )
        for u in users
    ]


@router.post("/invite", response_model=InviteResponse)
async def invite_user(
    request: InviteUserRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Invite a new user via email (admin only).
    """
    # Check if user already exists
    existing = db.query(User).filter(
        User.email == request.email.lower(),
        User.is_deleted == False,
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists",
        )

    # Validate role
    try:
        role = UserRole(request.role)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {[r.value for r in UserRole]}",
        )

    # Create user (without password - pending invite acceptance)
    user = User(
        email=request.email.lower(),
        first_name=request.first_name,
        last_name=request.last_name,
        role=role,
        is_active=True,
        email_verified=False,
        created_by=admin.id,
    )
    db.add(user)
    db.flush()  # Get the user ID

    # Generate invite token
    token = generate_token()
    invite = InviteToken(
        user_id=user.id,
        token=token,
        expires_at=datetime.utcnow() + timedelta(days=settings.invite_token_expire_days),
        created_by=admin.id,
    )
    db.add(invite)
    db.commit()

    # Send invite email
    email_service = get_email_service()
    inviter_name = f"{admin.first_name} {admin.last_name}".strip() if admin.first_name else admin.email
    email_service.send_invite_email(user.email, token, inviter_name)

    return InviteResponse(
        message="Invitation sent successfully",
        user_id=user.id,
        email=user.email,
    )


@router.get("/{user_id}", response_model=UserDetail)
async def get_user(
    user_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Get user details (admin only).
    """
    user = db.query(User).filter(
        User.id == user_id,
        User.is_deleted == False,
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserDetail(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role.value,
        is_active=user.is_active,
        email_verified=user.email_verified,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login_at=user.last_login_at,
        password_changed_at=user.password_changed_at,
    )


@router.put("/{user_id}", response_model=UserDetail)
async def update_user(
    user_id: str,
    request: UpdateUserRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Update user (admin only).
    """
    user = db.query(User).filter(
        User.id == user_id,
        User.is_deleted == False,
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Prevent self-demotion from admin
    if user_id == admin.id and request.role and request.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own admin role",
        )

    # Prevent self-deactivation
    if user_id == admin.id and request.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account",
        )

    # Update fields
    if request.first_name is not None:
        user.first_name = request.first_name
    if request.last_name is not None:
        user.last_name = request.last_name
    if request.role is not None:
        try:
            user.role = UserRole(request.role)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role. Must be one of: {[r.value for r in UserRole]}",
            )
    if request.is_active is not None:
        user.is_active = request.is_active

    user.updated_by = admin.id
    db.commit()

    return UserDetail(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role.value,
        is_active=user.is_active,
        email_verified=user.email_verified,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login_at=user.last_login_at,
        password_changed_at=user.password_changed_at,
    )


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Soft delete user (admin only).
    """
    user = db.query(User).filter(
        User.id == user_id,
        User.is_deleted == False,
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Prevent self-deletion
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )

    user.is_deleted = True
    user.is_active = False
    user.updated_by = admin.id
    db.commit()

    return {"message": "User deleted successfully"}


@router.post("/{user_id}/resend-invite")
async def resend_invite(
    user_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Resend invite email to a user who hasn't completed registration (admin only).
    """
    user = db.query(User).filter(
        User.id == user_id,
        User.is_deleted == False,
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User has already completed registration",
        )

    # Invalidate existing invites
    db.query(InviteToken).filter(
        InviteToken.user_id == user.id,
        InviteToken.used_at == None,
    ).update({"is_deleted": True})

    # Generate new invite token
    token = generate_token()
    invite = InviteToken(
        user_id=user.id,
        token=token,
        expires_at=datetime.utcnow() + timedelta(days=settings.invite_token_expire_days),
        created_by=admin.id,
    )
    db.add(invite)
    db.commit()

    # Send invite email
    email_service = get_email_service()
    inviter_name = f"{admin.first_name} {admin.last_name}".strip() if admin.first_name else admin.email
    email_service.send_invite_email(user.email, token, inviter_name)

    return {"message": "Invitation resent successfully"}
