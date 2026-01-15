"""
Database connection and session management.
"""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool

from app.config import get_settings
from app.db.models import Base

settings = get_settings()

# Use NullPool for serverless/Supabase compatibility
# For SQLite, use default pool
if settings.database_url.startswith("postgresql"):
    engine = create_engine(settings.database_url, poolclass=NullPool)
else:
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},  # Needed for SQLite
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency for getting database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """Context manager for database sessions (for use outside FastAPI)."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
