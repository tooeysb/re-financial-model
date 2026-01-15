"""
API routes for the financial model.
"""

from fastapi import APIRouter

from app.api import properties, scenarios, calculations

router = APIRouter()

# Include sub-routers
router.include_router(properties.router, prefix="/properties", tags=["properties"])
router.include_router(scenarios.router, prefix="/scenarios", tags=["scenarios"])
router.include_router(calculations.router, prefix="/calculate", tags=["calculations"])
