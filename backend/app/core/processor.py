import time
import logging
import asyncio
from typing import Optional
from pydantic import ValidationError

from app.models import ContactBase, ProcessingResult, EmailResult
from backend.app.core.beacon import MailBeacon
from app.core.domain_utils import extract_domain, normalize_url
from app.exceptions import (
    EmailSleuthError, InsufficientInputError, DomainExtractionError, UrlParseError
)

log = logging.getLogger(__name__)

async def process_record(beacon: MailBeacon, contact_input: ContactBase) -> ProcessingResult:
    """
    Processes a single contact record to find and verify an email address.

    Handles input validation, normalization, calls the core sleuth logic,
    and formats the final result including errors or skipped status.

    Args:
        beacon: An initialized MailBeacon instance.
        contact_input: The input contact data (Pydantic model).

    Returns:
        A ProcessingResult object.
    """
    start_time = asyncio.get_event_loop().time()
    task_id = f"Record: {contact_input.first_name or contact_input.full_name}@{contact_input.domain or contact_input.company}"
    log.info(f"[{task_id}] Starting processing.")

    # --- Input Validation and Normalization ---
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    domain_input_str: Optional[str] = None
    normalized_domain: Optional[str] = None
    normalized_url: Optional[str] = None

    try:
        # Prioritize explicit names, fallback to splitting full_name
        first_name = contact_input.first_name
        last_name = contact_input.last_name
        full_name = contact_input.full_name

        if not (first_name and last_name) and full_name:
            parts = full_name.split()
            if len(parts) >= 2:
                first_name = first_name or parts[0]
                last_name = last_name or parts[-1]
            elif len(parts) == 1:
                 # If only one part in full_name, use it for both if fn/ln are missing
                 first_name = first_name or parts[0]
                 last_name = last_name or parts[0]

        # Ensure names are not empty after potential derivation
        if not first_name or not last_name:
             raise InsufficientInputError("Could not determine valid first and last names.")

        # Get domain/URL input, preferring 'domain' over 'company_domain' alias
        domain_input_str = contact_input.domain # Alias handled by Pydantic

        if not domain_input_str:
             # This should be caught by Pydantic model validation, but double-check
             raise InsufficientInputError("Domain/company_domain is required.")

        # Normalize URL and extract domain
        normalized_url = normalize_url(domain_input_str) # Raises UrlParseError/InsufficientInputError
        normalized_domain = extract_domain(domain_input_str) # Raises DomainExtractionError

        log.debug(f"[{task_id}] Validated Input: FN='{first_name}', LN='{last_name}', Domain='{normalized_domain}', URL='{normalized_url}'")

        # --- Call Core Logic ---
        email_result: EmailResult = await beacon.find_email(
            first_name=first_name,
            last_name=last_name,
            domain=normalized_domain,
            website_url=normalized_url
        )

        processing_time = (asyncio.get_event_loop().time() - start_time) * 1000
        log.info(f"[{task_id}] ✓ Processing successful. Time: {processing_time:.2f}ms")

        # Construct successful result - convenience fields populated by Pydantic validator
        return ProcessingResult(
            contact_input=contact_input, # Return the original input
            email_discovery_results=email_result,
            processing_time_ms=processing_time
        )

    except (ValidationError, InsufficientInputError, DomainExtractionError, UrlParseError) as e:
        # Handle validation/normalization errors -> Skipped Result
        reason = f"Input validation/normalization failed: {e}"
        log.warning(f"[{task_id}] Skipping record. Reason: {reason}")
        processing_time = (asyncio.get_event_loop().time() - start_time) * 1000
        return ProcessingResult(
            contact_input=contact_input,
            email_finding_skipped=True,
            email_finding_reason=reason,
            processing_time_ms=processing_time
        )

    except EmailSleuthError as e:
        # Handle errors from the core sleuth logic -> Error Result
        log.error(f"[{task_id}] !!! Error during email finding: {e}", exc_info=False)
        processing_time = (asyncio.get_event_loop().time() - start_time) * 1000
        return ProcessingResult(
            contact_input=contact_input,
            email_finding_error=str(e), # Use the error message
            processing_time_ms=processing_time
        )
    except Exception as e:
         # Catch any other unexpected errors during processing
         log.exception(f"[{task_id}] !!! Unexpected critical error during processing: {e}") # Log traceback
         processing_time = (asyncio.get_event_loop().time() - start_time) * 1000
         return ProcessingResult(
             contact_input=contact_input,
             email_finding_error=f"Unexpected critical error: {e}",
             processing_time_ms=processing_time
         )
