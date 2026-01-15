"""
API routes for the financial model.
"""

from fastapi import APIRouter

from app.api import properties, scenarios, calculations, auth
from app.api.admin import users_router

router = APIRouter()

# Include sub-routers
router.include_router(properties.router, prefix="/properties", tags=["properties"])
router.include_router(scenarios.router, prefix="/scenarios", tags=["scenarios"])
router.include_router(calculations.router, prefix="/calculate", tags=["calculations"])

# Auth routes are included directly at /api/auth (defined in auth.py with prefix)
# Admin routes are included directly at /api/admin/users (defined in users.py with prefix)
