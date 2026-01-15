"""
Admin API module.
"""

from app.api.admin.users import router as users_router

__all__ = ["users_router"]
