"""
Main FastAPI application entry point.
"""

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from app.config import get_settings
from app.api import router as api_router

settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="Real estate financial modeling and underwriting platform",
    version="0.1.0",
    debug=settings.debug,
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/ui/static"), name="static")

# Set up templates
templates = Jinja2Templates(directory="app/ui/templates")

# Include API routes
app.include_router(api_router, prefix="/api")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Render the home page."""
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "title": settings.app_name},
    )


@app.get("/model/{model_id}", response_class=HTMLResponse)
async def model_view(request: Request, model_id: str):
    """Render the financial model editor."""
    return templates.TemplateResponse(
        "model.html",
        {"request": request, "model_id": model_id},
    )


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy", "version": "0.1.0"}
