import asyncio
import logging
import socket
from typing import List, Optional, NamedTuple
import aiodns
from app.config import Settings
from app.exceptions import DnsError, NxDomainError, NoDnsRecordsError, DnsTimeoutError

log = logging.getLogger(__name__)

class MailServer(NamedTuple):
    """Represents a mail server identified via DNS."""
    exchange: str
    preference: int

async def create_resolver(settings: Settings) -> aiodns.DNSResolver:
    """Creates and configures an aiodns resolver based on application settings."""
    # Note: aiodns doesn't directly support configuring multiple servers like trust-dns-resolver.
    # It typically uses the system's resolver configuration (/etc/resolv.conf on Linux/macOS, system settings on Windows).
    # We can specify nameservers, but the underlying pycares library handles the logic.
    # Timeout is handled per-query.
    try:
        resolver = aiodns.DNSResolver(nameservers=settings.dns_servers)
        log.debug(f"aiodns resolver configured with nameservers: {settings.dns_servers}")
        return resolver
    except aiodns.error.DNSError as e:
        log.error(f"Failed to initialize aiodns resolver: {e}")
        raise DnsError(f"Failed to initialize DNS resolver: {e}") from e

async def _query_with_timeout(resolver: aiodns.DNSResolver, query_type: str, domain: str, timeout: float):
    """Wrapper for aiodns query with explicit timeout."""
    try:
        return await asyncio.wait_for(resolver.query(domain, query_type), timeout=timeout)
    except asyncio.TimeoutError:
        log.warning(f"DNS {query_type} query for {domain} timed out after {timeout}s.")
        raise DnsTimeoutError(domain)
    except aiodns.error.DNSError as e:
        # Map aiodns errors to custom exceptions
        # Ref: https://github.com/saghul/aiodns/blob/master/aiodns/error.py
        # Ref: https://c-ares.org/ares_strerror.html
        err_code = e.args[0]
        err_str = e.args[1] if len(e.args) > 1 else str(e)

        if err_code == aiodns.error.ARES_ENOTFOUND or "NXDOMAIN" in err_str: # NXDOMAIN
            log.error(f"Domain {domain} does not exist (NXDOMAIN) during {query_type} lookup.")
            raise NxDomainError(domain) from e
        elif err_code == aiodns.error.ARES_ENODATA: # NoAnswer
            log.warning(f"No {query_type} records found (NoAnswer) for {domain}.")
            # Let the caller handle NoAnswer specifically (e.g., fallback for MX)
            raise NoDnsRecordsError(domain) from e # Raise specific error for NoAnswer
        elif err_code in [aiodns.error.ARES_ETIMEOUT]: # Explicit timeout code
             log.warning(f"DNS {query_type} query for {domain} timed out (ARES_ETIMEOUT).")
             raise DnsTimeoutError(domain) from e
        else:
            log.error(f"Unexpected DNS error during {query_type} lookup for {domain}: {err_code} {err_str}")
            raise DnsError(f"DNS {query_type} lookup failed for {domain}: {err_str} (Code: {err_code})") from e
    except Exception as e: # Catch potential other errors
        log.error(f"Unexpected error during DNS {query_type} query for {domain}: {e}")
        raise DnsError(f"Unexpected error during DNS {query_type} query for {domain}: {e}") from e


async def resolve_a_record_fallback(resolver: aiodns.DNSResolver, domain: str, settings: Settings) -> MailServer:
    """Attempts to resolve an A record for the domain as a fallback mail server."""
    log.debug(f"Attempting A record fallback for {domain}")
    try:
        a_records = await _query_with_timeout(resolver, 'A', domain, settings.dns_timeout)
        if a_records:
            # Use the first A record found
            mail_server_ip = str(a_records[0].host)
            log.info(f"Using A record for {domain} as mail server: {mail_server_ip}")
            # Preference MAX_INT equivalent for A record fallback
            return MailServer(exchange=mail_server_ip, preference=65535)
        else:
            # This case should be covered by ARES_ENODATA in _query_with_timeout
            log.error(f"A record lookup for {domain} returned empty list unexpectedly.")
            raise NoDnsRecordsError(domain)
    except NoDnsRecordsError:
         log.error(f"No MX or A records found for {domain}.")
         raise # Re-raise the specific error
    except (NxDomainError, DnsTimeoutError, DnsError) as e:
         log.error(f"A record fallback failed for {domain}: {e}")
         raise # Re-raise DNS errors


async def resolve_mail_server(resolver: aiodns.DNSResolver, domain: str, settings: Settings) -> MailServer:
    """
    Resolves the mail server(s) for a given domain, checking MX records first,
    then falling back to A records.

    Args:
        resolver: An initialized aiodns.DNSResolver.
        domain: The domain name to resolve.
        settings: Application settings containing timeouts.

    Returns:
        A MailServer named tuple containing the most preferred mail server.

    Raises:
        NxDomainError: If the domain does not exist.
        NoDnsRecordsError: If no MX or A records are found.
        DnsTimeoutError: If DNS queries time out.
        DnsError: For other unexpected DNS errors.
    """
    log.debug(f"Performing DNS MX lookup for {domain}")
    try:
        mx_records = await _query_with_timeout(resolver, 'MX', domain, settings.dns_timeout)

        if not mx_records:
             # Should be caught by ARES_ENODATA, but handle defensively
             log.warning(f"MX lookup for {domain} succeeded but returned no records. Trying A record fallback...")
             return await resolve_a_record_fallback(resolver, domain, settings)

        # Sort by preference (lower is better)
        mx_records.sort(key=lambda r: r.priority)

        best_mx = mx_records[0]
        exchange = str(best_mx.host).rstrip('.') # Clean trailing dot
        preference = int(best_mx.priority)

        if not exchange:
            log.error(f"Empty mail server name found in highest priority MX record for {domain}")
            raise NoDnsRecordsError(f"Empty exchange in MX record for {domain}")

        log.info(f"Found MX for {domain}: {exchange} (Pref: {preference})")
        return MailServer(exchange=exchange, preference=preference)

    except NoDnsRecordsError: # Specifically catch NoAnswer for MX
        log.warning(f"No MX records found (NoAnswer) for {domain}. Trying A record fallback...")
        return await resolve_a_record_fallback(resolver, domain, settings)
    except (NxDomainError, DnsTimeoutError, DnsError) as e:
        # Catch other DNS errors from _query_with_timeout or fallback
        log.error(f"DNS resolution failed for {domain}: {e}")
        raise # Re-raise the specific error

# Example usage (for testing purposes)
async def main():
    from app.config import Settings
    settings = Settings() # Load default settings
    resolver = await create_resolver(settings)
    try:
        # Example domains
        # mail_server = await resolve_mail_server(resolver, "google.com", settings)
        # print(f"Google.com Mail Server: {mail_server}")
        mail_server = await resolve_mail_server(resolver, "github.com", settings)
        print(f"Github.com Mail Server: {mail_server}")
        # mail_server = await resolve_mail_server(resolver, "nonexistentdomain12345abc.com", settings)
        # print(f"Nonexistent Mail Server: {mail_server}")
        # mail_server = await resolve_mail_server(resolver, "no-mx-but-a-record.com", settings) # Replace with actual domain if needed
        # print(f"No MX domain Mail Server: {mail_server}")

    except EmailSleuthError as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    # asyncio.run(main()) # Requires Python 3.7+
    # For older versions:
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
