import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
import aiohttp
from app.config import get_settings, Settings # Import get_settings and Settings
from backend.app.core.beacon import MailBeacon # Renamed from EmailSleuth
from app.core.dns_utils import create_resolver, DnsResolver # Import create_resolver
# Import SMTP test function if implemented separately, or add basic check here
# from app.core.smtp_utils import test_smtp_connectivity # Assuming this exists

log = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages application startup and shutdown events.
    Initializes shared resources like HTTP client, DNS resolver, and EmailSleuth service.
    """
    log.info("Application lifespan startup...")
    # --- Startup ---
    try:
        # 1. Load Settings (already loaded on import, just retrieve)
        settings: Settings = get_settings()
        app.state.settings = settings
        log.info("Settings loaded and attached to app state.")

        # 2. Initialize shared aiohttp ClientSession
        app.state.http_session = aiohttp.ClientSession(
            headers={"User-Agent": settings.user_agent},
            timeout=aiohttp.ClientTimeout(total=settings.request_timeout) # Set default timeout
        )
        log.info("aiohttp ClientSession initialized.")

        # 3. Initialize shared DNS Resolver
        app.state.dns_resolver = await create_resolver(settings)
        log.info("aiodns DNSResolver initialized.")

        # 4. Initialize EmailSleuth instance
        app.state.beacon = MailBeacon( # Renamed state key and class
            settings=settings,
            http_session=app.state.http_session,
            dns_resolver=app.state.dns_resolver # Pass the initialized resolver
        )
        log.info("MailBeacon service initialized.") # Updated log message

        # 5. Optional: SMTP Connectivity Test (add basic check or import)
        # try:
        #     # Placeholder: Implement a basic check or import test_smtp_connectivity
        #     # await test_smtp_connectivity(settings) # Assuming function exists
        #     log.info("SMTP connectivity test successful (placeholder).")
        # except Exception as e:
        #     log.error(f"SMTP connectivity test failed on startup: {e}")
        #     # Decide if this should prevent startup? For now, just log error.
        #     # raise RuntimeError(f"SMTP connectivity check failed: {e}") from e

        log.info("Application startup complete.")

    except Exception as e:
        log.exception("Critical error during application startup!")
        # Clean up any partially initialized resources if possible
        if hasattr(app.state, 'http_session') and not app.state.http_session.closed:
            await app.state.http_session.close()
        # Re-raise the exception to prevent the app from starting in a broken state
        raise RuntimeError(f"Application startup failed: {e}") from e

    yield # Application runs here

    # --- Shutdown ---
    log.info("Application lifespan shutdown...")
    if hasattr(app.state, 'http_session') and not app.state.http_session.closed:
        await app.state.http_session.close()
        log.info("aiohttp ClientSession closed.")
    # DNS resolver (aiodns) doesn't typically require explicit closing

    log.info("Application shutdown complete.")
