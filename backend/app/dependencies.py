import logging
from fastapi import Request, Depends
from app.config import Settings # Import the actual Settings class
from backend.app.core.beacon import MailBeacon # Renamed from EmailSleuth
from app.core.dns_utils import DnsResolver # Needed for type hint if stored separately

log = logging.getLogger(__name__)

# --- Dependency Functions ---

def get_settings(request: Request) -> Settings:
    """
    FastAPI dependency to get the application settings instance.
    Retrieves the settings stored in the application state during startup.
    """
    if not hasattr(request.app.state, 'settings'):
        log.critical("Settings object not found in application state. Lifespan startup might have failed.")
        # Depending on strictness, could raise an internal server error
        # For now, return a default instance, but this indicates a problem.
        # return Settings() # Fallback - less safe
        raise RuntimeError("Application settings not initialized. Check lifespan startup.")
    return request.app.state.settings

def get_dns_resolver(request: Request) -> DnsResolver:
    """
    FastAPI dependency to get the shared DNS resolver instance.
    """
    if not hasattr(request.app.state, 'dns_resolver'):
         raise RuntimeError("DNS resolver not initialized. Check lifespan startup.")
    return request.app.state.dns_resolver

def get_mail_beacon(request: Request) -> MailBeacon: # Renamed function and return type
    """
    FastAPI dependency to get the shared MailBeacon instance.
    Retrieves the instance stored in the application state during startup.
    """
    if not hasattr(request.app.state, 'beacon'): # Renamed state key
        log.critical("MailBeacon object not found in application state. Lifespan startup might have failed.")
        raise RuntimeError("MailBeacon service not initialized. Check lifespan startup.")
    return request.app.state.beacon # Renamed state key

# Example of using Depends within another dependency (if needed)
# async def get_some_other_service(settings: Settings = Depends(get_settings)):
#     # Use settings to initialize another service
#     pass
