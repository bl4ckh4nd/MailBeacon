import re
import logging
from typing import List, Set
from app.config import Settings # Import Settings to access regex

log = logging.getLogger(__name__)

def _sanitize_name_part(part: str) -> str:
    """Removes whitespace and converts to lowercase."""
    if not part:
        return ""
    return "".join(part.split()).lower()

def generate_email_patterns(first_name: str, last_name: str, domain: str, settings: Settings) -> List[str]:
    """
    Generates a list of common email address patterns for a given name and domain,
    similar to the Rust implementation.

    Args:
        first_name: The contact's first name.
        last_name: The contact's last name.
        domain: The company domain name (e.g., "example.com").
        settings: The application settings instance containing the email regex.

    Returns:
        A list of potential, unique, and valid email patterns.
    """
    log.debug(f"Generating patterns for {first_name} {last_name} @ {domain}")

    if not first_name or not last_name or not domain or '.' not in domain:
        log.warning(
            f"Cannot generate patterns due to empty name/domain or invalid domain: "
            f"'{first_name}' '{last_name}' @ '{domain}'"
        )
        return []

    first = _sanitize_name_part(first_name)
    last = _sanitize_name_part(last_name)

    if not first or not last:
        log.warning(
            f"Cannot generate patterns after sanitizing names: '{first}' '{last}' @ '{domain}'"
        )
        return []

    # Ensure initials are handled correctly even for single-character names
    first_initial = first[0] if first else ''
    last_initial = last[0] if last else ''

    # Use a set to automatically handle duplicates
    patterns_set: Set[str] = set()

    # Generate base patterns (local parts)
    local_parts = {
        f"{first}",                            # john
        f"{first}.{last}",                     # john.doe
        f"{first}{last}",                      # johndoe
        f"{last}.{first}",                     # doe.john
        f"{last}{first}",                      # doejohn
        f"{first_initial}{last}",              # jdoe
        f"{first_initial}.{last}",             # j.doe
        f"{first}{last_initial}",              # johnd
        f"{first}.{last_initial}",             # john.d
        f"{first}_{last}",                     # john_doe
        f"{first}-{last}",                     # john-doe
        f"{last}_{first}",                     # doe_john
        f"{last}-{first}",                     # doe-john
    }

    # Add patterns with truncated names if applicable
    if len(first) >= 3:
        local_parts.add(f"{first[:3]}{last}") # johdoe
    if len(last) >= 3:
        local_parts.add(f"{first}{last[:3]}") # johndoe

    # Combine local parts with domain and validate
    final_patterns: List[str] = []
    for lp in local_parts:
        if not lp: continue # Skip empty local parts
        email = f"{lp}@{domain}"
        if settings.email_regex.match(email):
            patterns_set.add(email)

    final_patterns = sorted(list(patterns_set)) # Sort for consistent output

    log.debug(f"Generated {len(final_patterns)} unique valid patterns.")
    return final_patterns


def extract_emails_from_text(text: str, settings: Settings) -> List[str]:
    """
    Extracts unique email addresses found within a block of text using the configured regex.

    Args:
        text: The text content to search within.
        settings: The application settings instance containing the email regex.

    Returns:
        A list of unique email addresses found.
    """
    if not text:
        return []

    # Use the compiled regex from settings
    found = settings.email_regex.findall(text)

    # Return unique emails in lowercase
    return sorted(list(set(email.lower() for email in found)))
