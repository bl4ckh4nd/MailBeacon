from typing import List, Optional, Dict, Any
from pydantic import BaseModel, EmailStr, Field, validator, root_validator

# --- Input Models ---

class ContactBase(BaseModel):
    """Base model for contact information provided in requests."""
    first_name: Optional[str] = Field(None, description="Contact's first name.")
    last_name: Optional[str] = Field(None, description="Contact's last name.")
    full_name: Optional[str] = Field(None, description="Contact's full name (if first/last not provided).")
    domain: Optional[str] = Field(None, description="Company domain (e.g., example.com) or website URL.", alias="company_domain") # Added alias
    company: Optional[str] = Field(None, description="Company name (optional).")
    other_fields: Optional[Dict[str, Any]] = Field(None, description="Catch-all for other input fields.")

    @root_validator(pre=True)
    def check_name_and_domain(cls, values):
        first, last, full = values.get('first_name'), values.get('last_name'), values.get('full_name')
        domain = values.get('domain') or values.get('company_domain')

        has_name = full or (first and last)
        has_domain = domain

        if not has_name:
            raise ValueError("Either 'full_name' or both 'first_name' and 'last_name' must be provided.")
        if not has_domain:
            raise ValueError("Either 'domain' or 'company_domain' must be provided.")
        return values

    class Config:
        allow_population_by_field_name = True # Allows using alias 'company_domain'

class SingleContactRequest(ContactBase):
    """Request model for finding email for a single contact."""
    pass

class BatchContactRequest(BaseModel):
    """Request model for finding emails for multiple contacts."""
    contacts: List[SingleContactRequest]

# --- Internal & Result Models ---

class FoundEmailData(BaseModel):
    """Represents a single email address found and its associated metadata."""
    email: EmailStr = Field(..., description="The discovered email address.")
    confidence: int = Field(..., ge=0, le=10, description="Likelihood score (0-10).")
    source: str = Field(..., description="Discovery method ('pattern' or 'scraped').")
    is_generic: bool = Field(..., description="Indicates if the email uses a common generic prefix.")
    verification_status: Optional[bool] = Field(None, description="SMTP verification result (True=Verified, False=Rejected, None=Inconclusive/Untested).")
    verification_message: str = Field(..., description="Message accompanying the verification status.")

class EmailResult(BaseModel):
    """Contains the detailed results of the email finding process for a single contact."""
    found_emails: List[FoundEmailData] = Field(default_factory=list, description="List of all potentially valid emails found, ordered by likelihood.")
    most_likely_email: Optional[EmailStr] = Field(None, description="The single email address deemed most likely.")
    confidence_score: int = Field(0, ge=0, le=10, description="Confidence score for the most_likely_email.")
    methods_used: List[str] = Field(default_factory=list, description="Discovery methods used (e.g., 'pattern_generation', 'website_scraping', 'smtp_verification').")
    verification_log: Dict[str, str] = Field(default_factory=dict, description="Log of SMTP verification attempts and outcomes.")

class ProcessingResult(BaseModel):
    """Final output structure combining input and results for a single contact."""
    contact_input: ContactBase = Field(..., description="The original contact information provided.")

    # Detailed results (optional if skipped/error before discovery)
    email_discovery_results: Optional[EmailResult] = Field(None, description="Detailed results of the email discovery process.")

    # Convenience fields mirroring EmailResult
    email: Optional[EmailStr] = Field(None, description="The primary email found (convenience field).")
    email_confidence: Optional[int] = Field(None, ge=0, le=10, description="Confidence score for the primary email (convenience field).")
    email_verification_method: Optional[str] = Field(None, description="Comma-separated list of methods used (convenience field).")
    email_alternatives: List[EmailStr] = Field(default_factory=list, description="List of alternative emails found (convenience field).")

    # Status/Error fields
    email_finding_skipped: bool = Field(False, description="Flag indicating if processing was skipped due to missing input.")
    email_finding_reason: Optional[str] = Field(None, description="Reason why processing was skipped.")
    email_verification_failed: bool = Field(False, description="Flag indicating verification failed definitively for top choices.")
    email_finding_error: Optional[str] = Field(None, description="Error message if processing failed unexpectedly.")

    # Performance field
    processing_time_ms: Optional[float] = Field(None, description="Time taken to process the record in milliseconds.")

    @root_validator(pre=False, skip_on_failure=True)
    def populate_convenience_fields(cls, values):
        """Populate top-level convenience fields from email_discovery_results."""
        results = values.get('email_discovery_results')
        if results:
            values['email'] = results.most_likely_email
            values['email_confidence'] = results.confidence_score if results.most_likely_email else None
            values['email_verification_method'] = ", ".join(results.methods_used) if results.methods_used else None
            values['email_alternatives'] = [
                e.email for e in results.found_emails
                if Some(e.email) != results.most_likely_email
            ][:5] # Limit alternatives for convenience field, adjust limit as needed
            values['email_verification_failed'] = results.most_likely_email is None and bool(results.found_emails)

        # Ensure contact_input is always present
        if 'contact_input' not in values:
             # This case should ideally not happen if validation runs correctly,
             # but as a fallback, create a default ContactBase.
             # Consider logging a warning here.
             values['contact_input'] = ContactBase() # Or handle more gracefully

        return values

# Helper for validator logic
def Some(value):
    return value is not None


