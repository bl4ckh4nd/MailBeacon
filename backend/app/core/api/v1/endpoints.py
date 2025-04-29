import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.models import (
    SingleContactRequest,
    BatchContactRequest,
    ProcessingResult,
    ContactBase # Import ContactBase for error handling in batch
)
from backend.app.core.beacon import MailBeacon
# Correct dependency function name as defined in dependencies.py
from app.dependencies import get_mail_beacon
from app.core.processor import process_record
# Import base exception for try-except blocks if needed, but rely on handler
from app.exceptions import EmailSleuthError

log = logging.getLogger(__name__)
router = APIRouter()

@router.post(
    "/find-single", # Renamed endpoint
    response_model=ProcessingResult,
    summary="Find Email for Single Contact",
    description="Accepts details for a single contact and attempts to find and verify their email address."
)
async def find_single_email(
    contact: SingleContactRequest,
    # Use the correct dependency function name
    beacon: MailBeacon = Depends(get_mail_beacon)
) -> ProcessingResult:
    """
    Finds and verifies the email address for a single contact.
    Relies on the global exception handler for EmailSleuthError.
    """
    # No try-except needed here if the global handler is registered in main.py
    # The exception will propagate and be handled by email_sleuth_exception_handler
    return await process_record(beacon, contact)

@router.post(
    "/find-batch", # Renamed endpoint
    response_model=List[ProcessingResult],
    summary="Find Emails for Multiple Contacts (Batch)",
    description="Accepts a list of contacts and processes them concurrently to find email addresses."
)
async def find_emails_batch(
    request: BatchContactRequest,
    # Use the correct dependency function name
    beacon: MailBeacon = Depends(get_mail_beacon)
) -> List[ProcessingResult]:
    """
    Finds emails for multiple contacts concurrently using asyncio.gather.
    Handles individual processing errors gracefully within the batch.
    """
    if not request.contacts:
        return []

    # Create tasks for concurrent processing
    tasks = [process_record(beacon, contact) for contact in request.contacts]

    # Run tasks concurrently and gather results
    # return_exceptions=True allows us to capture errors for individual tasks
    results_or_errors = await asyncio.gather(*tasks, return_exceptions=True)

    final_results: List[ProcessingResult] = []
    for i, result_or_error in enumerate(results_or_errors):
        original_contact = request.contacts[i] # Get corresponding input contact
        if isinstance(result_or_error, Exception):
            # If process_record raised an exception, log it and create an error result
            # Note: This error won't be caught by the global handler as it's inside gather
            log.error(f"Error processing contact {i} in batch: {result_or_error}", exc_info=False) # Set exc_info=False if too verbose
            # Create a ProcessingResult indicating the error
            error_message = f"Processing failed: {result_or_error}"
            if isinstance(result_or_error, EmailSleuthError):
                 # Use the specific message if it's a known error type
                 error_message = str(result_or_error)

            final_results.append(ProcessingResult(
                contact_input=original_contact,
                email_finding_error=error_message
                # processing_time_ms might not be available here
            ))
        elif isinstance(result_or_error, ProcessingResult):
            # If process_record completed (even if it resulted in skipped/error internally)
            final_results.append(result_or_error)
        else:
             # Should not happen with return_exceptions=True, but handle defensively
             log.error(f"Unexpected result type for contact {i} in batch: {type(result_or_error)}")
             final_results.append(ProcessingResult(
                 contact_input=original_contact,
                 email_finding_error="Unexpected error during batch processing."
             ))

    return final_results

@router.get(
    "/health",
    summary="Health Check",
    description="Simple health check endpoint.",
    response_description="Returns the operational status of the API."
)
async def health_check():
    """Returns a simple health status."""
    return {"status": "ok"}
