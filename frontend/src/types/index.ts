// Mirroring pythonRefactor/app/models.py
// Note: EmailStr from Pydantic is mapped to string in TypeScript.

export interface ContactBase {
  first_name?: string | null;
  last_name?: string | null;
  full_name?: string | null;
  domain?: string | null; // API handles alias 'company_domain'
  company?: string | null;
  // other_fields is omitted as it's unlikely to be used directly in the basic UI
}

export interface SingleContactRequest extends ContactBase {}

export interface BatchContactRequest {
  contacts: SingleContactRequest[];
}

export interface FoundEmailData {
  email: string;
  confidence: number; // Assuming range 0-10 based on plan
  source: string;
  is_generic: boolean;
  verification_status?: boolean | null;
  verification_message: string;
}

export interface EmailResult {
  found_emails: FoundEmailData[];
  most_likely_email?: string | null;
  confidence_score: number; // Assuming range 0-10 based on plan
  methods_used: string[];
  verification_log: Record<string, string>;
}

export interface ProcessingResult {
  contact_input: ContactBase;
  email_discovery_results?: EmailResult | null;

  // Convenience fields mirroring backend model structure
  email?: string | null;
  email_confidence?: number | null; // Assuming range 0-10
  email_verification_method?: string | null; // Note: Backend sends this as comma-separated string
  email_alternatives: string[];

  // Status/Error fields
  email_finding_skipped: boolean;
  email_finding_reason?: string | null;
  email_verification_failed: boolean; // Derived on backend
  email_finding_error?: string | null;

  // Performance field
  processing_time_ms?: number | null; // Backend uses float, frontend uses number
}

// Enum for client-side status interpretation
export enum ResultStatus {
    Success = 'Success',
    NotFound = 'Not Found', // Represents cases where email is null/empty but no error/skip
    Skipped = 'Skipped',
    Error = 'Error',
    Processing = 'Processing', // For intermediate state e.g., in batch
    Verified = 'Verified', // Added for clarity based on ResultDisplay logic
    Rejected = 'Rejected', // Added for clarity based on ResultDisplay logic
    Inconclusive = 'Inconclusive' // Added for clarity based on ResultDisplay logic
}
