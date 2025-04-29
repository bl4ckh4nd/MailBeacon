# MailBeacon 🕵️📧

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen)](https://github.com/<your-username>/<your-repo>) <!-- Replace with actual build badge -->
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE) <!-- Add a LICENSE file -->
[![Issues](https://img.shields.io/github/issues/<your-username>/<your-repo>)](https://github.com/<your-username>/<your-repo>/issues) <!-- Replace with your repo path -->

**Find and verify professional email addresses with confidence.**

MailBeacon is a tool designed to discover the most likely email address for a contact associated with a specific company domain or website. It employs multiple strategies including pattern generation, website scraping, DNS checks, and SMTP verification to achieve this.

---

⚠️ **Work in Progress** 🚧
> This project is currently under active development. Features may change, and some parts might be incomplete or contain bugs. Feedback and contributions are welcome!

---

## ✨ Features

*   **Multi-Strategy Discovery:** Combines common email pattern generation and website scraping to gather potential email candidates.
*   **Robust Verification:**
    *   Performs DNS MX record lookups (with A record fallback) to find the correct mail servers.
    *   Uses SMTP `RCPT TO` checks to verify if an email address is accepted by the server.
    *   Includes basic catch-all domain detection.
    *   Handles SMTP retries for inconclusive results (e.g., temporary failures, greylisting).
*   **Confidence Scoring:** Assigns a likelihood score (0-10) to each found email based on source (pattern vs. scraped), name matching, SMTP verification results, and whether it's a generic address (e.g., `info@`, `contact@`).
*   **Intelligent Selection:** Chooses the "most likely" email based on confidence thresholds, prioritizing verified, non-generic addresses.
*   **API Interface:** Provides a FastAPI backend with endpoints for single contact lookups and batch processing.
*   **Web UI:** Includes a React/TypeScript frontend with Tailwind CSS for interacting with the API (single lookups, batch uploads via CSV).
*   **Configurable:** Allows tuning parameters like timeouts, concurrency, DNS servers, scraped pages, and confidence thresholds via environment variables and a TOML configuration file.
*   **Asynchronous:** Built with async libraries (FastAPI, aiohttp, aiodns, aiosmtplib) for efficient I/O operations.

## 🏗️ Architecture

MailBeacon consists of two main parts:

1.  **Backend (Python/FastAPI):**
    *   Located in the `backend/` directory.
    *   Provides the core logic for email discovery and verification.
    *   Exposes a RESTful API for the frontend or other clients.
    *   Uses `Pydantic` for data validation, `aiohttp` for scraping, `aiodns` for DNS lookups, and `aiosmtplib` for SMTP checks.
2.  **Frontend (React/TypeScript/Vite):**
    *   Located in the `frontend/` directory.
    *   Provides a web-based user interface to interact with the backend API.
    *   Built with React, TypeScript, Vite, and styled with Tailwind CSS (with some potential MUI remnants).
    *   Includes pages for finding single emails and batch processing via CSV upload.

## 🚀 Getting Started

Follow these instructions to set up and run MailBeacon on your local machine.

### Prerequisites

*   **Git:** To clone the repository.
*   **Python:** Version 3.7+ (due to `asyncio` usage and type hinting).
*   **Pip:** Python package installer (usually comes with Python).
*   **Node.js:** Version 16+ (or as required by Vite/React dependencies).
*   **npm** or **yarn:** Node.js package manager.

### Installation

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/<your-username>/<your-repo>.git
    cd <your-repo>
    ```

2.  **Backend Setup:**
    ```bash
    # Navigate to the backend directory
    cd backend

    # Create and activate a virtual environment (recommended)
    python -m venv venv
    # On Windows:
    # venv\Scripts\activate
    # On macOS/Linux:
    # source venv/bin/activate

    # Install Python dependencies
    pip install -r requirements.txt
    ```
    ```text
    # backend/requirements.txt
    fastapi>=0.68.0,<0.69.0
    uvicorn[standard]>=0.15.0,<0.16.0
    aiohttp[speedups]>=3.8.0,<3.9.0
    aiosmtplib>=1.1.6,<1.2.0
    beautifulsoup4>=4.9.3,<4.10.0
    lxml>=4.9.0,<4.10.0
    tomli>=2.0.1,<2.1.0
    pydantic>=1.10.0,<2.0.0
    aiofiles>=0.8.0,<0.9.0
    python-dotenv>=0.19.0,<0.20.0
    aiodns>=3.0.0,<3.1.0
    ```

3.  **Frontend Setup:**
    ```bash
    # Navigate to the frontend directory (from the project root)
    cd ../frontend

    # Install Node.js dependencies
    npm install
    # or
    # yarn install

    # Create a local environment file for the API URL (optional, defaults to localhost:8000)
    # Copy .env.example to .env.local (if example exists) or create .env.local
    ```
    Create a `.env.local` file in the `frontend/` directory if your backend API runs on a different URL:
    ```env
    # frontend/.env.local
    VITE_API_URL=http://localhost:8000
    ```

### Running the Application

1.  **Run the Backend API:**
    *   Ensure your virtual environment is activated (`source venv/bin/activate` or `venv\Scripts\activate`).
    *   Navigate to the `backend/` directory.
    *   Start the FastAPI server using Uvicorn:
        ```bash
        # Recommended for development (with auto-reload)
        uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
        # Or using the run script
        # python run.py
        ```
        ```python
        # backend/run.py
        import uvicorn

        if __name__ == "__main__":
            uvicorn.run(
                "app.main:app",
                host="0.0.0.0",
                port=8000,
                reload=True
            )

        ```
    *   The API will be available at `http://localhost:8000`.
    *   API documentation (Swagger UI) is available at `http://localhost:8000/docs`.

2.  **Run the Frontend UI:**
    *   Navigate to the `frontend/` directory.
    *   Start the Vite development server:
        ```bash
        npm run dev
        # or
        # yarn dev
        ```
    *   The frontend application will typically be available at `http://localhost:5173` (Vite's default) or another port if 5173 is busy. Check the terminal output for the exact URL.

## 🤔 How It Works

MailBeacon follows these steps to find and verify an email address:

1.  **Input:** Receives contact details (First Name + Last Name OR Full Name, and a Domain/Website URL) via the API.
2.  **Validation & Normalization:**
    *   Ensures required fields are present.
    *   Normalizes the website URL (adds scheme if missing).
    *   Extracts the base domain name from the URL/domain input.
3.  **Pattern Generation:** Creates a list of common email address patterns using the provided name and domain (e.g., `f.last@domain.com`, `firstlast@domain.com`).
    ```python
    # backend/app/core/patterns.py
    # ...
    def generate_email_patterns(first_name: str, last_name: str, domain: str, settings: Settings) -> List[str]:
        # ... (Generates patterns like f.last, firstlast, flast, etc.)
        local_parts = {
            f"{first}",                            # john
            f"{first}.{last}",                     # john.doe
            # ... other patterns
        }
        # ... (Combines with domain, validates format)
        return sorted(list(patterns_set))
    # ...
    ```
4.  **Website Scraping:**
    *   Uses `aiohttp` to asynchronously fetch the homepage of the provided website URL.
    *   Also fetches common pages specified in the configuration (e.g., `/about`, `/contact`, `/team`).
    *   Parses the HTML content using `BeautifulSoup` (with `lxml`).
    *   Extracts potential email addresses using regex and from `mailto:` links.
    *   Filters scraped emails to keep those matching the target domain or known generic emails.
    ```python
    # backend/app/core/scraper.py
    # ...
    class Scraper:
        # ...
        async def scrape_website_for_emails(self, base_url_str: str) -> List[str]:
            # ... (Normalizes URL, generates list of URLs to visit)
            urls_to_visit.add(normalized_base_url)
            for page_path in self.settings.common_pages_to_scrape:
                # ... add urljoin(normalized_base_url, page_path)
            # ... (Fetches pages with _fetch_page)
            # ... (Extracts emails with _extract_emails_from_html using regex and BeautifulSoup)
            return final_emails
    # ...
    ```
5.  **Candidate Consolidation:** Combines emails found from patterns and scraping into a unique, prioritized list (emails containing name parts are often checked first).
6.  **DNS Resolution:**
    *   Uses `aiodns` to look up MX (Mail Exchanger) records for the target domain.
    *   Sorts MX records by preference.
    *   If no MX records are found, it falls back to looking up the A (Address) record for the domain itself.
    ```python
    # backend/app/core/dns_utils.py
    # ...
    async def resolve_mail_server(resolver: aiodns.DNSResolver, domain: str, settings: Settings) -> MailServer:
        # ... (Query MX records using _query_with_timeout)
        try:
            mx_records = await _query_with_timeout(resolver, 'MX', domain, settings.dns_timeout)
            # ... (Sort by preference, return best MailServer)
        except NoDnsRecordsError:
            # ... (Fallback to A record lookup)
            return await resolve_a_record_fallback(resolver, domain, settings)
    # ...
    ```
7.  **SMTP Verification:**
    *   Connects to the identified mail server on port 25 using `aiosmtplib`.
    *   Sends `EHLO`, `MAIL FROM` (using a configured sender address), and `RCPT TO` (for the candidate email) commands.
    *   **Catch-all Check:** If the target email is accepted (2xx code), it may send another `RCPT TO` with a random, unlikely username for the same domain to check if the server accepts *any* address.
    *   **Interprets Results:**
        *   `2xx` (Success): Email likely exists (or it's a catch-all).
        *   `5xx` (Permanent Failure, e.g., "User unknown", "Mailbox unavailable"): Email likely does not exist.
        *   `4xx` (Temporary Failure): Inconclusive (e.g., greylisting, server busy).
    *   **Retries:** If the result is inconclusive (e.g., 4xx, timeout, potential catch-all), it may retry the check up to `max_verification_attempts` times with delays.
    ```python
    # backend/app/core/smtp_utils.py
    # ...
    class SmtpVerifier:
        # ...
        async def _verify_single_attempt(self, email: str, domain: str, mail_server: MailServer) -> SmtpVerificationResultInternal:
            # ... (Connect, EHLO, MAIL FROM)
            code, msg = await smtp_client.mail(self.settings.smtp_sender_email)
            # ... (RCPT TO for target email)
            target_code, target_msg = await smtp_client.rcpt(email)
            # ... (Optional RCPT TO for random email - catch-all detection)
            # ... (Interpret target_code: 2xx, 4xx, 5xx)
            # ... (Return SmtpVerificationResultInternal: conclusive/inconclusive, retry needed?, catch-all?)

        async def verify_email_with_retries(self, email: str) -> Tuple[Optional[bool], str, bool]:
            # ... (Get mail server)
            for attempt in range(self.settings.max_verification_attempts):
                result = await self._verify_single_attempt(...)
                if result.exists is not None or not result.should_retry:
                    break # Stop on conclusive or non-retriable
                # ... (Sleep if retrying)
            return last_result, last_message, is_catch_all
    # ...
    ```
8.  **Scoring & Selection:**
    *   Each potential email is scored (0-10) based on:
        *   Source: Scraped emails (especially if matching name) get higher initial scores than patterned ones.
        *   Verification: Successful SMTP verification adds a significant boost; failure results in a score of 0; inconclusive results might add a small boost or penalty (e.g., if catch-all suspected).
        *   Name Match: Presence of the first or last name in the local part.
        *   Generic Prefix: Penalty applied if the email uses a generic prefix (e.g., `info@`, `contact@`).
    *   Emails are sorted by score (descending), non-generic preferred over generic, scraped preferred over pattern (as tie-breakers).
    *   The highest-scoring **non-generic** email above `confidence_threshold` is selected as "most likely".
    *   If no non-generic meets the threshold, the highest-scoring **generic** email might be selected *if* it meets the higher `generic_confidence_threshold`.
    ```python
    # backend/app/core/beacon.py
    # ...
    class MailBeacon:
        # ...
        async def find_email(...):
            # ... (Generate patterns, scrape website)
            # ... (Combine candidates)
            for email in all_candidates:
                # ... Calculate base_confidence based on source, name_in_email, etc.
                # ... Apply penalty if is_generic
                if should_verify_smtp:
                     # ... Call smtp_verifier.verify_email_with_retries
                     # ... Adjust confidence based on verification_status (boost/reset/small boost)
                # ... Store final confidence (0-10) in FoundEmailData if > 0

            # ... Sort verified_emails_data by confidence, non-generic, source
            # ... Select most_likely_email based on thresholds
            return results
    # ...
    ```
9.  **Result Formatting:** The final result (`ProcessingResult`) includes the original input, the most likely email (if found), its confidence score, alternative emails, methods used, status flags (skipped/error), and processing time.

## 🔌 API Endpoints

The backend exposes the following main endpoints under the `/api/v1` prefix (configurable):

*   `POST /find-single`
    *   **Description:** Finds the email for a single contact.
    *   **Request Body:** `SingleContactRequest` JSON object.
    *   **Response:** `ProcessingResult` JSON object.
*   `POST /find-batch`
    *   **Description:** Finds emails for multiple contacts concurrently.
    *   **Request Body:** `BatchContactRequest` JSON object containing a list of contacts.
    *   **Response:** A list of `ProcessingResult` JSON objects.
*   `GET /health`
    *   **Description:** Simple health check endpoint.
    *   **Response:** `{"status": "ok"}`

```python
# backend/app/core/api/v1/endpoints.py
# ...
router = APIRouter()

@router.post("/find-single", response_model=ProcessingResult)
async def find_single_email(contact: SingleContactRequest, beacon: MailBeacon = Depends(get_mail_beacon)):
    # ... calls process_record(beacon, contact)
    pass

@router.post("/find-batch", response_model=List[ProcessingResult])
async def find_emails_batch(request: BatchContactRequest, beacon: MailBeacon = Depends(get_mail_beacon)):
    # ... creates asyncio tasks for process_record(beacon, contact) for each contact
    # ... runs tasks with asyncio.gather
    pass

@router.get("/health")
async def health_check():
    return {"status": "ok"}
# ...
```

## ⚙️ Configuration

The backend can be configured via:

1.  **Environment Variables:** Prefixed with `MAILBEACON_` (e.g., `MAILBEACON_DEBUG=true`, `MAILBEACON_SMTP_TIMEOUT=10`). Case-insensitive.
2.  **`.env` File:** Loads environment variables from a `.env` file in the `backend/` directory.
3.  **TOML Configuration File:** Looks for `mailbeacon.toml` or `config.toml` in the current directory (`backend/`), or `~/.config/mailbeacon.toml`. Values from TOML are overridden by environment variables.

Key configurable settings (see `backend/app/config.py` for defaults and details):

*   `debug`: Enable debug logging.
*   `max_concurrency`: Max concurrent tasks for batch processing.
*   `request_timeout`: Timeout for HTTP scraping requests.
*   `smtp_timeout`: Timeout for SMTP connection/commands.
*   `dns_timeout`: Timeout for DNS queries.
*   `min_sleep_between_requests` / `max_sleep_between_requests`: Delay between scraping/verification requests.
*   `common_pages_to_scrape`: List of paths to check during scraping.
*   `user_agent`: User agent string for scraping.
*   `dns_servers`: List of DNS servers for resolution.
*   `smtp_sender_email`: Sender address for SMTP `MAIL FROM`.
*   `max_verification_attempts`: Retries for inconclusive SMTP checks.
*   `confidence_threshold`: Min score (0-10) for selecting a non-generic email.
*   `generic_confidence_threshold`: Min score (0-10) for selecting a generic email.
*   `generic_email_prefixes`: Set of prefixes considered generic (e.g., "info", "contact").

**Example `mailbeacon.toml`:**

```toml
# backend/mailbeacon.toml (example)
debug = false

[network]
request_timeout = 15
min_sleep = 0.2
max_sleep = 1.0
user_agent = "MyCustomBot/1.0"

[dns]
dns_timeout = 7
dns_servers = ["1.1.1.1", "9.9.9.9"]

[smtp]
smtp_timeout = 8
max_verification_attempts = 1 # Reduce retries

[scraping]
common_pages = ["/contact", "/about", "/people"]
generic_email_prefixes = ["info", "contact", "hello", "support", "sales"] # Override defaults

[verification]
confidence_threshold = 5
generic_confidence_threshold = 8
max_concurrency = 10
```

```python
# backend/app/config.py
import os
import re
import logging
from typing import Optional, List, Tuple, Set, Dict, Any
from pydantic import BaseSettings, EmailStr, Field, validator, root_validator
import tomli # Use tomli for TOML parsing

# ... (DEFAULT values)

class Settings(BaseSettings):
    # ... (Field definitions for all settings)

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        case_sensitive = False
        env_prefix = "MAILBEACON_"

    # ... (Validators, including root_validator to load from TOML)

# ... (Singleton instance creation)
settings = Settings()

def get_settings() -> Settings:
    return settings
```

## 🤝 Contributing

Contributions are welcome! Please feel free to open an issue or submit a pull request.

1.  Fork the repository.
2.  Create a new branch (`git checkout -b feature/your-feature-name`).
3.  Make your changes.
4.  Commit your changes (`git commit -am 'Add some feature'`).
5.  Push to the branch (`git push origin feature/your-feature-name`).
6.  Open a Pull Request.

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
