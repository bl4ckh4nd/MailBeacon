import logging
from urllib.parse import urlparse, ParseResult
from app.exceptions import DomainExtractionError, UrlParseError, InsufficientInputError

log = logging.getLogger(__name__)

def extract_domain(url_str: str) -> str:
    """
    Extracts the base domain name (e.g., "example.com") from a given URL string.
    Handles missing schemes, "www." prefixes, and ports.

    Args:
        url_str: The input URL string.

    Returns:
        The lowercase domain name.

    Raises:
        DomainExtractionError: If the URL is empty, cannot be parsed, or has no host.
    """
    log.debug(f"Attempting to extract domain from URL: {url_str}")
    if not url_str:
        log.warning("Received empty website URL for domain extraction.")
        raise DomainExtractionError("Input URL string is empty")

    # Add scheme if missing for robust parsing
    url_str_with_scheme = url_str
    if not url_str.startswith("http://") and not url_str.startswith("https://"):
        url_str_with_scheme = f"https://{url_str}"

    try:
        parsed_url: ParseResult = urlparse(url_str_with_scheme)
    except ValueError as e:
        # Handle potential rare ValueError during parsing itself
        log.error(f"Failed to parse URL '{url_str_with_scheme}' (original: {url_str}): {e}")
        raise DomainExtractionError(f"Could not parse URL: {url_str_with_scheme}") from e

    # Use .netloc which includes hostname and potentially port
    host = parsed_url.netloc
    if not host:
        # Check hostname specifically if netloc is empty (e.g., "http://")
        host = parsed_url.hostname
        if not host:
             log.warning(f"Could not extract host from parsed URL: {url_str_with_scheme}")
             raise DomainExtractionError(f"Could not extract host from parsed URL: {url_str_with_scheme}")

    # Remove port if present
    if ":" in host:
        host = host.split(":", 1)[0]

    # Remove 'www.' prefix if present
    domain = host.removeprefix("www.")

    final_domain = domain.lower()

    if not final_domain: # Should be rare after previous checks
         log.error(f"Domain extraction resulted in empty string for input: {url_str}")
         raise DomainExtractionError(f"Extracted domain is empty for URL: {url_str}")

    log.debug(f"Extracted domain '{final_domain}' from '{url_str}'")
    return final_domain


def normalize_url(url_str: str) -> str:
    """
    Parses the input website string into a valid URL string, adding https scheme if necessary.

    Args:
        url_str: The input URL string.

    Returns:
        A normalized URL string with a scheme.

    Raises:
        InsufficientInputError: If the input URL string is empty.
        UrlParseError: If the URL cannot be parsed after adding a scheme.
    """
    if not url_str:
        raise InsufficientInputError("Website URL is empty")

    url_str_with_scheme = url_str
    if not url_str.startswith("http://") and not url_str.startswith("https://"):
        url_str_with_scheme = f"https://{url_str}"

    # Basic check for validity after adding scheme
    try:
        parsed = urlparse(url_str_with_scheme)
        if not parsed.scheme or not parsed.netloc:
            raise UrlParseError(f"Invalid URL structure after normalization: {url_str_with_scheme}")
    except ValueError as e:
        raise UrlParseError(f"Failed to parse normalized URL '{url_str_with_scheme}': {e}") from e

    return url_str_with_scheme
