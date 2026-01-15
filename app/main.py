"""
Main FastAPI application entry point.
"""

from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from app.config import get_settings
from app.api import router as api_router
from app.api.auth import router as auth_router
from app.api.admin.users import router as admin_users_router
from app.db.database import init_db

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    # Startup: Initialize database
    init_db()
    yield
    # Shutdown: cleanup if needed


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="Real estate financial modeling and underwriting platform",
    version="0.1.0",
    debug=settings.debug,
    lifespan=lifespan,
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/ui/static"), name="static")

# Set up templates
templates = Jinja2Templates(directory="app/ui/templates")

# Include API routes
app.include_router(api_router, prefix="/api")
app.include_router(auth_router)  # /api/auth/* (prefix defined in router)
app.include_router(admin_users_router)  # /api/admin/users/* (prefix defined in router)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Render the home page."""
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "title": settings.app_name},
    )


@app.get("/model/{model_id}", response_class=HTMLResponse)
async def model_view(
    request: Request, model_id: str, property_id: Optional[str] = None
):
    """Render the financial model editor."""
    return templates.TemplateResponse(
        "model.html",
        {"request": request, "model_id": model_id, "property_id": property_id or ""},
    )


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy", "version": "0.1.0"}


# === Auth Page Routes ===

@app.get("/auth/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Render the login page."""
    return templates.TemplateResponse("auth/login.html", {"request": request})


@app.get("/auth/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Render the registration page."""
    return templates.TemplateResponse("auth/register.html", {"request": request})


@app.get("/auth/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request):
    """Render the forgot password page."""
    return templates.TemplateResponse("auth/forgot-password.html", {"request": request})


@app.get("/auth/reset-password", response_class=HTMLResponse)
async def reset_password_page(request: Request):
    """Render the reset password page."""
    return templates.TemplateResponse("auth/reset-password.html", {"request": request})
