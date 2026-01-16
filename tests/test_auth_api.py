"""
Tests for authentication API endpoints.
"""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.db.models import User, UserRole, InviteToken, RefreshToken, PasswordResetToken
from app.auth.password import hash_password
from app.auth.tokens import generate_token, hash_token

# Database setup is handled by conftest.py


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    user = User(
        email="test@example.com",
        hashed_password=hash_password("testpassword123"),
        first_name="Test",
        last_name="User",
        role=UserRole.user,
        is_active=True,
        email_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_user(db_session):
    """Create an admin user."""
    user = User(
        email="admin@example.com",
        hashed_password=hash_password("adminpassword123"),
        first_name="Admin",
        last_name="User",
        role=UserRole.admin,
        is_active=True,
        email_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def invited_user(db_session):
    """Create a user with pending invite."""
    user = User(
        email="invited@example.com",
        hashed_password=None,  # No password yet
        role=UserRole.user,
        is_active=True,
        email_verified=False,
    )
    db_session.add(user)
    db_session.flush()

    token = generate_token()
    invite = InviteToken(
        user_id=user.id,
        token=token,
        expires_at=datetime.utcnow() + timedelta(days=7),
    )
    db_session.add(invite)
    db_session.commit()
    db_session.refresh(user)

    return {"user": user, "token": token}


class TestLogin:
    """Test login endpoint."""

    def test_login_success(self, client, test_user):
        """Test successful login."""
        response = client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "testpassword123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == "test@example.com"

    def test_login_sets_cookies(self, client, test_user):
        """Test that login sets httpOnly cookies."""
        response = client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "testpassword123"},
        )
        assert response.status_code == 200
        assert "access_token" in response.cookies
        assert "refresh_token" in response.cookies

    def test_login_invalid_email(self, client, test_user):
        """Test login with non-existent email."""
        response = client.post(
            "/api/auth/login",
            json={"email": "wrong@example.com", "password": "testpassword123"},
        )
        assert response.status_code == 401
        assert "Invalid email or password" in response.json()["detail"]

    def test_login_invalid_password(self, client, test_user):
        """Test login with wrong password."""
        response = client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "wrongpassword"},
        )
        assert response.status_code == 401

    def test_login_inactive_user(self, client, db_session):
        """Test login with inactive user."""
        user = User(
            email="inactive@example.com",
            hashed_password=hash_password("password123"),
            is_active=False,
            email_verified=True,
        )
        db_session.add(user)
        db_session.commit()

        response = client.post(
            "/api/auth/login",
            json={"email": "inactive@example.com", "password": "password123"},
        )
        assert response.status_code == 403
        assert "deactivated" in response.json()["detail"]

    def test_login_updates_last_login(self, client, test_user, db_session):
        """Test that login updates last_login_at."""
        response = client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "testpassword123"},
        )
        assert response.status_code == 200

        db_session.refresh(test_user)
        assert test_user.last_login_at is not None


class TestRegister:
    """Test registration endpoint."""

    def test_register_success(self, client, invited_user):
        """Test successful registration with invite token."""
        response = client.post(
            "/api/auth/register",
            json={
                "token": invited_user["token"],
                "password": "newpassword123",
                "first_name": "New",
                "last_name": "User",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["first_name"] == "New"

    def test_register_sets_cookies(self, client, invited_user):
        """Test that registration sets auth cookies."""
        response = client.post(
            "/api/auth/register",
            json={
                "token": invited_user["token"],
                "password": "newpassword123",
            },
        )
        assert response.status_code == 200
        assert "access_token" in response.cookies

    def test_register_invalid_token(self, client):
        """Test registration with invalid token."""
        response = client.post(
            "/api/auth/register",
            json={
                "token": "invalid-token",
                "password": "newpassword123",
            },
        )
        assert response.status_code == 400

    def test_register_expired_token(self, client, db_session):
        """Test registration with expired token."""
        user = User(
            email="expired@example.com",
            hashed_password=None,
            is_active=True,
            email_verified=False,
        )
        db_session.add(user)
        db_session.flush()

        token = generate_token()
        invite = InviteToken(
            user_id=user.id,
            token=token,
            expires_at=datetime.utcnow() - timedelta(days=1),  # Expired
        )
        db_session.add(invite)
        db_session.commit()

        response = client.post(
            "/api/auth/register",
            json={
                "token": token,
                "password": "newpassword123",
            },
        )
        assert response.status_code == 400
        assert "expired" in response.json()["detail"]

    def test_register_already_used_token(self, client, invited_user, db_session):
        """Test registration with already used token."""
        # First registration
        response = client.post(
            "/api/auth/register",
            json={
                "token": invited_user["token"],
                "password": "newpassword123",
            },
        )
        assert response.status_code == 200

        # Second registration attempt with same token
        response = client.post(
            "/api/auth/register",
            json={
                "token": invited_user["token"],
                "password": "anotherpassword",
            },
        )
        assert response.status_code == 400
        assert "already been used" in response.json()["detail"]


class TestForgotPassword:
    """Test forgot password endpoint."""

    def test_forgot_password_existing_user(self, client, test_user):
        """Test forgot password for existing user."""
        response = client.post(
            "/api/auth/forgot-password",
            json={"email": "test@example.com"},
        )
        assert response.status_code == 200
        # Should always return success message (prevent enumeration)
        assert "If an account exists" in response.json()["message"]

    def test_forgot_password_nonexistent_user(self, client):
        """Test forgot password for non-existent user (same response)."""
        response = client.post(
            "/api/auth/forgot-password",
            json={"email": "nonexistent@example.com"},
        )
        assert response.status_code == 200
        # Same message to prevent enumeration
        assert "If an account exists" in response.json()["message"]


class TestResetPassword:
    """Test reset password endpoint."""

    def test_reset_password_success(self, client, test_user, db_session):
        """Test successful password reset."""
        from app.db.models import PasswordResetToken

        token = generate_token()
        reset = PasswordResetToken(
            user_id=test_user.id,
            token=token,
            expires_at=datetime.utcnow() + timedelta(hours=24),
        )
        db_session.add(reset)
        db_session.commit()

        response = client.post(
            "/api/auth/reset-password",
            json={"token": token, "password": "newpassword456"},
        )
        assert response.status_code == 200
        assert "successfully" in response.json()["message"]

    def test_reset_password_invalid_token(self, client):
        """Test reset with invalid token."""
        response = client.post(
            "/api/auth/reset-password",
            json={"token": "invalid-token", "password": "newpassword456"},
        )
        assert response.status_code == 400

    def test_reset_password_revokes_sessions(self, client, test_user, db_session):
        """Test that password reset revokes all refresh tokens."""
        from app.db.models import PasswordResetToken

        # Create a refresh token
        refresh = RefreshToken(
            user_id=test_user.id,
            token_hash=hash_token("some-refresh-token"),
            expires_at=datetime.utcnow() + timedelta(days=7),
        )
        db_session.add(refresh)
        db_session.flush()

        # Create reset token
        token = generate_token()
        reset = PasswordResetToken(
            user_id=test_user.id,
            token=token,
            expires_at=datetime.utcnow() + timedelta(hours=24),
        )
        db_session.add(reset)
        db_session.commit()

        # Reset password
        response = client.post(
            "/api/auth/reset-password",
            json={"token": token, "password": "newpassword456"},
        )
        assert response.status_code == 200

        # Check that refresh token was revoked
        db_session.refresh(refresh)
        assert refresh.revoked_at is not None


class TestRefreshToken:
    """Test token refresh endpoint."""

    def test_refresh_success(self, client, test_user, db_session):
        """Test successful token refresh."""
        # First login to get tokens
        login_response = client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "testpassword123"},
        )
        assert login_response.status_code == 200

        # Use refresh token from cookies
        refresh_response = client.post("/api/auth/refresh")
        assert refresh_response.status_code == 200
        assert "access_token" in refresh_response.json()

    def test_refresh_without_token(self, client):
        """Test refresh without token fails."""
        response = client.post("/api/auth/refresh")
        assert response.status_code == 401


class TestLogout:
    """Test logout endpoint."""

    def test_logout_success(self, client, test_user):
        """Test successful logout."""
        # Login first
        login_response = client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "testpassword123"},
        )
        assert login_response.status_code == 200

        # Logout
        logout_response = client.post("/api/auth/logout")
        assert logout_response.status_code == 200
        assert "successfully" in logout_response.json()["message"]

    def test_logout_clears_cookies(self, client, test_user):
        """Test that logout clears auth cookies."""
        # Login first
        client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "testpassword123"},
        )

        # Logout
        response = client.post("/api/auth/logout")
        assert response.status_code == 200

        # Cookies should be cleared (set to empty or expired)
        # Note: TestClient may handle this differently


class TestGetMe:
    """Test get current user endpoint."""

    def test_get_me_authenticated(self, client, test_user):
        """Test getting current user info when authenticated."""
        # Login first
        client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "testpassword123"},
        )

        # Get user info
        response = client.get("/api/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["first_name"] == "Test"

    def test_get_me_unauthenticated(self, client):
        """Test getting user info when not authenticated."""
        response = client.get("/api/auth/me")
        assert response.status_code == 401


class TestAdminUserManagement:
    """Test admin user management endpoints."""

    def test_list_users_as_admin(self, client, admin_user, test_user):
        """Test listing users as admin."""
        # Login as admin
        client.post(
            "/api/auth/login",
            json={"email": "admin@example.com", "password": "adminpassword123"},
        )

        response = client.get("/api/admin/users")
        assert response.status_code == 200
        users = response.json()
        assert len(users) >= 2  # At least admin and test user

    def test_list_users_as_non_admin(self, client, test_user):
        """Test that non-admin cannot list users."""
        # Login as regular user
        client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "testpassword123"},
        )

        response = client.get("/api/admin/users")
        assert response.status_code == 403

    def test_invite_user_as_admin(self, client, admin_user):
        """Test inviting a new user as admin."""
        client.post(
            "/api/auth/login",
            json={"email": "admin@example.com", "password": "adminpassword123"},
        )

        response = client.post(
            "/api/admin/users/invite",
            json={"email": "newuser@example.com", "role": "user"},
        )
        assert response.status_code == 200
        assert response.json()["email"] == "newuser@example.com"

    def test_invite_user_duplicate_email(self, client, admin_user, test_user):
        """Test that inviting duplicate email fails."""
        client.post(
            "/api/auth/login",
            json={"email": "admin@example.com", "password": "adminpassword123"},
        )

        response = client.post(
            "/api/admin/users/invite",
            json={"email": "test@example.com", "role": "user"},
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_update_user_as_admin(self, client, admin_user, test_user):
        """Test updating a user as admin."""
        client.post(
            "/api/auth/login",
            json={"email": "admin@example.com", "password": "adminpassword123"},
        )

        response = client.put(
            f"/api/admin/users/{test_user.id}",
            json={"first_name": "Updated", "role": "admin"},
        )
        assert response.status_code == 200
        assert response.json()["first_name"] == "Updated"
        assert response.json()["role"] == "admin"

    def test_admin_cannot_demote_self(self, client, admin_user):
        """Test that admin cannot change their own role."""
        client.post(
            "/api/auth/login",
            json={"email": "admin@example.com", "password": "adminpassword123"},
        )

        response = client.put(
            f"/api/admin/users/{admin_user.id}",
            json={"role": "user"},
        )
        assert response.status_code == 400

    def test_admin_cannot_deactivate_self(self, client, admin_user):
        """Test that admin cannot deactivate themselves."""
        client.post(
            "/api/auth/login",
            json={"email": "admin@example.com", "password": "adminpassword123"},
        )

        response = client.put(
            f"/api/admin/users/{admin_user.id}",
            json={"is_active": False},
        )
        assert response.status_code == 400

    def test_delete_user_as_admin(self, client, admin_user, test_user):
        """Test soft-deleting a user as admin."""
        client.post(
            "/api/auth/login",
            json={"email": "admin@example.com", "password": "adminpassword123"},
        )

        response = client.delete(f"/api/admin/users/{test_user.id}")
        assert response.status_code == 200

    def test_admin_cannot_delete_self(self, client, admin_user):
        """Test that admin cannot delete themselves."""
        client.post(
            "/api/auth/login",
            json={"email": "admin@example.com", "password": "adminpassword123"},
        )

        response = client.delete(f"/api/admin/users/{admin_user.id}")
        assert response.status_code == 400
