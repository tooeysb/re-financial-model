#!/usr/bin/env python3
"""
Create the initial admin user from environment variables.

This script should be run once during initial deployment to create
the first admin user who can then invite other users.

Usage:
    python scripts/create_initial_admin.py

Environment variables (from .env.development or .env.production):
    INITIAL_ADMIN_EMAIL - Email for the admin user
    INITIAL_ADMIN_PASSWORD - Password for the admin user
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime

from app.config import get_settings
from app.db.database import get_db_context, init_db
from app.db.models import User, UserRole
from app.auth.password import hash_password


def create_initial_admin():
    """Create the initial admin user if it doesn't exist."""
    settings = get_settings()

    # Check if admin credentials are configured
    if not settings.initial_admin_email or not settings.initial_admin_password:
        print("Error: INITIAL_ADMIN_EMAIL and INITIAL_ADMIN_PASSWORD must be set")
        print("Please configure these in your .env.development or .env.production file")
        sys.exit(1)

    # Validate password length
    if len(settings.initial_admin_password) < 8:
        print("Error: INITIAL_ADMIN_PASSWORD must be at least 8 characters")
        sys.exit(1)

    # Initialize database tables
    init_db()

    with get_db_context() as db:
        # Check if user already exists
        existing = db.query(User).filter(
            User.email == settings.initial_admin_email.lower()
        ).first()

        if existing:
            if existing.role == UserRole.admin:
                print(f"Admin user already exists: {existing.email}")
                return
            else:
                # Upgrade existing user to admin
                existing.role = UserRole.admin
                existing.updated_at = datetime.utcnow()
                db.commit()
                print(f"Upgraded existing user to admin: {existing.email}")
                return

        # Create new admin user
        admin = User(
            email=settings.initial_admin_email.lower(),
            hashed_password=hash_password(settings.initial_admin_password),
            first_name="Admin",
            last_name="User",
            role=UserRole.admin,
            is_active=True,
            email_verified=True,  # Admin user is pre-verified
            password_changed_at=datetime.utcnow(),
        )

        db.add(admin)
        db.commit()

        print(f"Successfully created admin user: {admin.email}")
        print("You can now log in at /auth/login")


if __name__ == "__main__":
    create_initial_admin()
