import os
import re
import logging
from typing import Optional, List, Tuple, Set, Dict, Any
from pydantic import BaseSettings, EmailStr, Field, validator, root_validator
import tomli # Use tomli for TOML parsing

# Configure logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# Default values similar to Rust's Config::default()
DEFAULT_COMMON_PAGES = [
    "/contact", "/contact-us", "/contactus", "/contact_us",
    "/about", "/about-us", "/aboutus", "/about_us",
    "/team", "/our-team", "/our_team", "/meet-the-team",
    "/people", "/staff", "/company", "/imprint"
    # German additions
    "/kontakt", "/impressum", "/ueber-uns", "/ueber_uns", 
    "/karriere", "/datenschutz",
]

DEFAULT_GENERIC_PREFIXES = {
    "info", "contact", "hello", "help", "support", "admin", "office",
    "sales", "press", "media", "marketing", "jobs", "careers", "hiring",
    "privacy", "security", "legal", "membership", "team", "people",
    "general", "feedback", "enquiries", "inquiries", "mail", "email",
    "pitch", "invest", "investors", "ir", "webmaster", "newsletter",
    "apply", "partner", "partners", "ventures",
    # German additions
    "kontakt", "hallo", "hilfe", "buero", 
    "vertrieb", "presse", "karriere", "datenschutz", "recht",
    "allgemein", "anfragen", "post"
}

DEFAULT_DNS_SERVERS = ["8.8.8.8", "8.8.4.4", "1.1.1.1", "1.0.0.1"]
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
DEFAULT_EMAIL_REGEX = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"

class Settings(BaseSettings):
    # --- Application Settings ---
    app_name: str = Field("MailBeacon API", description="Name of the application.")
    app_version: str = Field("0.1.0", description="Application version.")
    debug: bool = Field(False, description="Enable debug logging and potentially other debug features.")

    # --- API Settings ---
    api_prefix: str = Field("/api/v1", description="Prefix for all API routes.")

    # --- Concurrency ---
    max_concurrency: int = Field(8, ge=1, description="Maximum number of concurrent processing tasks.")

    # --- Network Timeouts (seconds) ---
    request_timeout: int = Field(10, ge=1, description="Timeout for individual HTTP requests.")
    smtp_timeout: int = Field(5, ge=1, description="Timeout for establishing SMTP connections and commands.")
    dns_timeout: int = Field(5, ge=1, description="Timeout for DNS resolution queries.")

    # --- Rate Limiting & Delays ---
    min_sleep_between_requests: float = Field(0.1, ge=0, description="Minimum sleep duration between HTTP requests (seconds).")
    max_sleep_between_requests: float = Field(0.5, ge=0, description="Maximum sleep duration between HTTP requests (seconds).")
    sleep_between_requests: Tuple[float, float] = (0.1, 0.5) # Derived field

    # --- Scraping ---
    common_pages_to_scrape: List[str] = Field(default_factory=lambda: list(DEFAULT_COMMON_PAGES), description="Common sub-pages to check during scraping.")
    user_agent: str = Field(DEFAULT_USER_AGENT, description="User agent string for HTTP requests.")

    # --- DNS ---
    dns_servers: List[str] = Field(default_factory=lambda: list(DEFAULT_DNS_SERVERS), description="DNS servers to use for resolution.")

    # --- SMTP ---
    smtp_sender_email: EmailStr = Field("verify-probe@example.com", description="Sender email address for SMTP MAIL FROM command.")
    max_verification_attempts: int = Field(2, ge=1, description="Maximum SMTP verification attempts for an inconclusive email.")

    # --- Verification & Scoring ---
    confidence_threshold: int = Field(4, ge=0, le=10, description="Confidence score threshold to select an email as 'most likely'.")
    generic_confidence_threshold: int = Field(7, ge=0, le=10, description="Confidence score above which a generic email might be selected.")
    max_alternatives: int = Field(5, ge=0, description="Maximum number of alternative emails to list in the output.")
    generic_email_prefixes: Set[str] = Field(default_factory=lambda: set(DEFAULT_GENERIC_PREFIXES), description="Set of common generic email prefixes.")

    # --- Internal ---
    email_regex_pattern: str = Field(DEFAULT_EMAIL_REGEX, description="Regex pattern for matching email addresses.")
    email_regex: re.Pattern = Field(re.compile(DEFAULT_EMAIL_REGEX), description="Compiled regex pattern for emails.") # Compiled regex

    # --- Configuration File ---
    config_file: Optional[str] = Field(None, description="Path to an optional TOML configuration file.")

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        # Allow reading settings from environment variables (case-insensitive)
        case_sensitive = False
        # Prefix for environment variables (e.g., EMAIL_SLEUTH_DEBUG=true)
        env_prefix = "MAILBEACON_"

    # --- Validators ---
    @validator('email_regex_pattern')
    def compile_email_regex(cls, v: str, values: Dict[str, Any]) -> str:
        try:
            values['email_regex'] = re.compile(v)
        except re.error as e:
            raise ValueError(f"Invalid email regex pattern: {e}")
        return v

    @validator('dns_servers', 'common_pages_to_scrape', pre=True, always=True)
    def split_comma_separated_list(cls, v):
        if isinstance(v, str):
            return [item.strip() for item in v.split(',') if item.strip()]
        return v

    @root_validator(skip_on_failure=True)
    def load_from_toml_and_validate(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        config_file_path = values.get('config_file')
        loaded_toml_config = {}

        # Try loading from specified file or default locations
        potential_paths = []
        if config_file_path:
            potential_paths.append(config_file_path)
        else:
            potential_paths.extend([
                "./mailbeacon.toml",
                "./config.toml",
                os.path.expanduser("~/.config/mailbeacon.toml")
            ])

        for path in potential_paths:
            try:
                if os.path.exists(path):
                    with open(path, "rb") as f:
                        loaded_toml_config = tomli.load(f)
                    log.info(f"Loaded configuration from TOML file: {path}")
                    break # Stop after finding the first valid file
            except FileNotFoundError:
                continue # Expected if file doesn't exist
            except tomli.TOMLDecodeError as e:
                log.warning(f"Failed to parse TOML configuration from {path}: {e}. Skipping this file.")
            except Exception as e:
                log.warning(f"Error reading configuration file {path}: {e}. Skipping this file.")

        # Apply TOML config, prioritizing environment variables and explicit settings
        # Pydantic BaseSettings handles env vars automatically. We layer TOML under it.
        toml_settings = cls._parse_toml_config(loaded_toml_config)

        # Update values dict: TOML values are used if not set by env vars/defaults
        for key, value in toml_settings.items():
             # Only update if the key exists in the model and wasn't explicitly set by env/defaults
             # Pydantic v1 logic: check if value is different from default AND not from env
             # This is tricky with BaseSettings. A simpler approach for now:
             # If the key is in values and is NOT the default value for that field, assume it was set by env/init.
             # Otherwise, allow TOML to override.
             field = cls.__fields__.get(key)
             if field and key not in values.keys(): # If not set by env/init
                 values[key] = value
             elif field and values.get(key) == field.default: # If set to default, allow TOML override
                 values[key] = value


        # --- Final Validations (similar to Rust's validate_config) ---
        min_sleep = values.get('min_sleep_between_requests', 0.1)
        max_sleep = values.get('max_sleep_between_requests', 0.5)
        if min_sleep > max_sleep:
            log.warning(f"Min sleep ({min_sleep}) > max sleep ({max_sleep}). Setting max = min.")
            values['max_sleep_between_requests'] = min_sleep
            max_sleep = min_sleep
        values['sleep_between_requests'] = (min_sleep, max_sleep)

        if not values.get('dns_servers'):
            log.warning("DNS servers list is empty. Setting to default public DNS servers.")
            values['dns_servers'] = list(DEFAULT_DNS_SERVERS)

        conf_thresh = values.get('confidence_threshold', 4)
        gen_conf_thresh = values.get('generic_confidence_threshold', 7)
        if conf_thresh > 10:
            log.warning("Confidence threshold > 10. Setting to 10.")
            values['confidence_threshold'] = 10
            conf_thresh = 10
        if gen_conf_thresh > 10:
            log.warning("Generic confidence threshold > 10. Setting to 10.")
            values['generic_confidence_threshold'] = 10
            gen_conf_thresh = 10
        if gen_conf_thresh < conf_thresh:
            log.warning(f"Generic confidence threshold ({gen_conf_thresh}) < base threshold ({conf_thresh}). Setting generic = base.")
            values['generic_confidence_threshold'] = conf_thresh

        if values.get('max_concurrency', 8) == 0:
             log.warning("Concurrency was set to 0. Setting to 1.")
             values['max_concurrency'] = 1

        # Re-compile regex if pattern changed via TOML
        if 'email_regex_pattern' in toml_settings:
             pattern = values['email_regex_pattern']
             try:
                 values['email_regex'] = re.compile(pattern)
             except re.error as e:
                 raise ValueError(f"Invalid email regex pattern from TOML: {e}")


        log.debug(f"Final configuration values: {values}")
        return values

    @classmethod
    def _parse_toml_config(cls, toml_data: Dict[str, Any]) -> Dict[str, Any]:
        """Flattens TOML structure and maps to Settings fields."""
        settings_map = {}
        # Map TOML sections/keys to Settings fields (adjust as needed)
        mapping = {
            ("network", "request_timeout"): "request_timeout",
            ("network", "min_sleep"): "min_sleep_between_requests",
            ("network", "max_sleep"): "max_sleep_between_requests",
            ("network", "user_agent"): "user_agent",
            ("dns", "dns_timeout"): "dns_timeout",
            ("dns", "dns_servers"): "dns_servers",
            ("smtp", "smtp_timeout"): "smtp_timeout",
            ("smtp", "smtp_sender_email"): "smtp_sender_email",
            ("smtp", "max_verification_attempts"): "max_verification_attempts",
            ("scraping", "common_pages"): "common_pages_to_scrape",
            ("scraping", "generic_email_prefixes"): "generic_email_prefixes",
            ("verification", "confidence_threshold"): "confidence_threshold",
            ("verification", "generic_confidence_threshold"): "generic_confidence_threshold",
            ("verification", "max_alternatives"): "max_alternatives",
            ("verification", "max_concurrency"): "max_concurrency",
            # Add direct mappings if needed, e.g., ("debug",): "debug"
        }

        for (section, key), settings_key in mapping.items():
            if section in toml_data and key in toml_data[section]:
                settings_map[settings_key] = toml_data[section][key]

        # Handle potential direct keys in TOML root (less common)
        # for key in cls.__fields__:
        #     if key in toml_data and isinstance(toml_data[key], (str, int, float, bool, list)):
        #          if key not in settings_map: # Avoid overwriting section values
        #              settings_map[key] = toml_data[key]

        # Convert set fields if loaded as list from TOML
        if 'generic_email_prefixes' in settings_map and isinstance(settings_map['generic_email_prefixes'], list):
            settings_map['generic_email_prefixes'] = set(settings_map['generic_email_prefixes'])

        return settings_map


# --- Singleton Instance ---
# Load settings once on import
try:
    settings = Settings()
    log.info("Configuration loaded successfully.")
except Exception as e:
    log.error(f"CRITICAL: Failed to load configuration on startup: {e}")
    # Fallback to defaults if loading fails catastrophically
    settings = Settings() # Or raise the error depending on desired behavior


def get_settings() -> Settings:
    """Dependency function to get the loaded settings."""
    return settings

