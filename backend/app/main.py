import logging
from fastapi import FastAPI
from app.lifespan import lifespan # Import the lifespan context manager
from app.core.api.v1.endpoints import router as v1_router # Import the v1 router
from app.exceptions import register_exception_handlers # Import handler registration function
from app.config import settings # Import settings for metadata

# Configure logging basic setup if not done elsewhere
# logging.basicConfig(level=logging.INFO if not settings.debug else logging.DEBUG)
log = logging.getLogger(__name__)

# Create FastAPI app instance with lifespan management
app = FastAPI(
    title=settings.app_name,
    description="API for finding and verifying professional email addresses based on contact information.",
    version=settings.app_version, # Fetches 'MailBeacon API' from settings
    lifespan=lifespan # Register the lifespan handler
)

# Register custom exception handlers
register_exception_handlers(app)
log.info("Custom exception handlers registered.")

# Include the API router
app.include_router(v1_router, prefix=settings.api_prefix) # Use prefix from settings
log.info(f"Included API router with prefix: {settings.api_prefix}")

# Root endpoint for basic check
@app.get("/", tags=["Root"], summary="Root Endpoint", description="Provides a basic welcome message.")
async def root():
    """Basic welcome endpoint."""
    # Uses settings.app_name which should now be 'MailBeacon API'
    return {"message": f"Welcome to {settings.app_name}. Visit /docs for documentation."}

# Add any other global middleware or configurations here if needed

log.info(f"{settings.app_name} initialization complete.")

# To run the app (from the project root directory 'email-sleuth'):
# uvicorn pythonRefactor.app.main:app --reload --host 0.0.0.0 --port 8000
