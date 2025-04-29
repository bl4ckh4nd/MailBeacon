from fastapi import HTTPException, status, Request
from fastapi.responses import JSONResponse
from typing import Union

# --- Custom Exception Classes ---

class EmailSleuthError(Exception):
    """Base exception for all email sleuth errors."""
    def __init__(self, message: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR):
        self.message = message
        self.status_code = status_code
        super().__init__(message)

class ConfigError(EmailSleuthError):
    """Error occurring during configuration loading or validation."""
    def __init__(self, message: str):
        super().__init__(f"Configuration Error: {message}", status.HTTP_500_INTERNAL_SERVER_ERROR)

class IoError(EmailSleuthError):
    """Error related to file input/output operations."""
    def __init__(self, message: str):
        super().__init__(f"IO Error: {message}", status.HTTP_500_INTERNAL_SERVER_ERROR)

class JsonError(EmailSleuthError):
    """Error during JSON serialization or deserialization."""
    def __init__(self, message: str):
        super().__init__(f"JSON Error: {message}", status.HTTP_400_BAD_REQUEST)

class UrlParseError(EmailSleuthError):
    """Error parsing a URL."""
    def __init__(self, message: str):
        super().__init__(f"URL Parsing Error: {message}", status.HTTP_400_BAD_REQUEST)

class RequestError(EmailSleuthError):
    """Error making HTTP requests (e.g., via aiohttp)."""
    def __init__(self, message: str):
        super().__init__(f"HTTP Request Error: {message}", status.HTTP_502_BAD_GATEWAY)

class HtmlParseError(EmailSleuthError):
    """Error parsing HTML content."""
    def __init__(self, message: str):
        super().__init__(f"HTML Parsing Error: {message}", status.HTTP_500_INTERNAL_SERVER_ERROR)

class DnsError(EmailSleuthError):
    """Base error for DNS resolution issues."""
    def __init__(self, message: str, status_code: int = status.HTTP_503_SERVICE_UNAVAILABLE):
        super().__init__(f"DNS Resolution Error: {message}", status_code)

class NxDomainError(DnsError):
    """Specific DNS error indicating the domain does not exist."""
    def __init__(self, domain: str):
        super().__init__(f"Domain Not Found (NXDOMAIN): {domain}", status.HTTP_404_NOT_FOUND)

class NoDnsRecordsError(DnsError):
    """Specific DNS error indicating no relevant records were found (MX/A)."""
    def __init__(self, domain: str):
        super().__init__(f"No DNS Records Found (MX/A): {domain}", status.HTTP_404_NOT_FOUND)

class DnsTimeoutError(DnsError):
    """DNS operation timed out."""
    def __init__(self, domain: str):
        super().__init__(f"DNS Timeout for domain: {domain}", status.HTTP_504_GATEWAY_TIMEOUT)

class SmtpError(EmailSleuthError):
    """Base error for SMTP communication issues."""
    def __init__(self, message: str, status_code: int = status.HTTP_503_SERVICE_UNAVAILABLE):
        super().__init__(f"SMTP Error: {message}", status_code)

class SmtpCommandError(SmtpError):
    """Error related to SMTP command execution details."""
    def __init__(self, code: int, message: str):
        super().__init__(f"SMTP Command Error: Code={code}, Message='{message}'", status.HTTP_503_SERVICE_UNAVAILABLE)

class SmtpTlsError(SmtpError):
    """Error specifically during the STARTTLS handshake."""
    def __init__(self, message: str):
        super().__init__(f"SMTP STARTTLS Error: {message}", status.HTTP_503_SERVICE_UNAVAILABLE)

class SmtpTemporaryFailureError(SmtpError):
    """SMTP verification returned a temporary failure (e.g., 4xx code)."""
    def __init__(self, message: str):
        super().__init__(f"SMTP Temporary Failure: {message}", status.HTTP_503_SERVICE_UNAVAILABLE)

class SmtpPermanentFailureError(SmtpError):
    """SMTP verification returned a permanent failure (e.g., 5xx code, user unknown)."""
    def __init__(self, message: str):
        super().__init__(f"SMTP Permanent Failure: {message}", status.HTTP_404_NOT_FOUND) # Treat as not found for API

class SmtpInconclusiveError(SmtpError):
    """SMTP verification was inconclusive (e.g., catch-all, timeout, non-standard response)."""
    def __init__(self, message: str):
        super().__init__(f"SMTP Inconclusive: {message}", status.HTTP_503_SERVICE_UNAVAILABLE)

class AddrParseError(EmailSleuthError):
    """Error parsing an IP address or socket address."""
    def __init__(self, message: str):
        super().__init__(f"Address Parsing Error: {message}", status.HTTP_500_INTERNAL_SERVER_ERROR)

class TaskError(EmailSleuthError):
    """Error related to concurrency or task execution."""
    def __init__(self, message: str):
        super().__init__(f"Task Execution Error: {message}", status.HTTP_500_INTERNAL_SERVER_ERROR)

class InsufficientInputError(EmailSleuthError):
    """Indicates insufficient input data to proceed."""
    def __init__(self, message: str):
        super().__init__(f"Insufficient Input Data: {message}", status.HTTP_400_BAD_REQUEST)

class DomainExtractionError(EmailSleuthError):
    """Failed to extract a domain from the provided URL."""
    def __init__(self, message: str):
        super().__init__(f"Failed to extract domain from URL: {message}", status.HTTP_400_BAD_REQUEST)


# --- FastAPI Exception Handlers ---

async def email_sleuth_exception_handler(request: Request, exc: EmailSleuthError):
    """Generic handler for EmailSleuthError and its subclasses."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )

# You can add more specific handlers if needed, but the base handler covers all subclasses.
# Example of a specific handler (though likely not needed with the base handler):
# async def nx_domain_exception_handler(request: Request, exc: NxDomainError):
#     return JSONResponse(
#         status_code=status.HTTP_404_NOT_FOUND,
#         content={"detail": exc.message},
#     )

def register_exception_handlers(app):
    """Registers all custom exception handlers with the FastAPI app."""
    app.add_exception_handler(EmailSleuthError, email_sleuth_exception_handler)
    # Add specific handlers here if you defined them above, e.g.:
    # app.add_exception_handler(NxDomainError, nx_domain_exception_handler)
