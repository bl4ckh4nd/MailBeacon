import asyncio
import logging
from typing import List, Set
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from app.config import Settings
from app.exceptions import RequestError, HtmlParseError
from app.core.patterns import extract_emails_from_text
from app.core.domain_utils import normalize_url # To ensure URLs are well-formed

log = logging.getLogger(__name__)

class Scraper:
    def __init__(self, session: aiohttp.ClientSession, settings: Settings):
        """
        Initializes the Scraper.

        Args:
            session: An existing aiohttp.ClientSession.
            settings: The application settings instance.
        """
        self.session = session
        self.settings = settings
        self.headers = {"User-Agent": self.settings.user_agent}

    async def _fetch_page(self, url: str) -> Optional[str]:
        """Fetches the content of a single page."""
        log.debug(f"Attempting to GET: {url}")
        try:
            async with self.session.get(
                url,
                headers=self.headers,
                timeout=self.settings.request_timeout,
                allow_redirects=True, # Follow redirects
                max_redirects=self.settings.scraping_max_redirects,
            ) as response:
                log.debug(f"GET {url} status: {response.status}")
                response.raise_for_status() # Raise exception for 4xx/5xx status codes

                content_type = response.headers.get(aiohttp.hdrs.CONTENT_TYPE, "").lower()
                if "html" not in content_type:
                    log.debug(f"Skipping non-HTML content at {url} ({content_type})")
                    return None

                # Read response text respecting charset if provided, default utf-8
                try:
                    # Use read() for bytes, then decode manually for better control
                    content_bytes = await response.read()
                    # Try decoding with specified charset, fallback to utf-8
                    charset = response.charset or 'utf-8'
                    try:
                        html_content = content_bytes.decode(charset)
                    except UnicodeDecodeError:
                         log.warning(f"Failed to decode {url} with charset {charset}, falling back to utf-8 with error handling.")
                         html_content = content_bytes.decode('utf-8', errors='replace')

                    return html_content
                except Exception as e:
                     log.warning(f"Failed to read/decode content from {url}: {e}")
                     raise HtmlParseError(f"Failed to read/decode content from {url}: {e}") from e

        except asyncio.TimeoutError:
            log.warning(f"Timeout scraping {url}")
            # Optionally raise a specific timeout error or just return None/empty
            return None # Treat timeout as page not successfully scraped
        except aiohttp.ClientResponseError as e:
            # Handle HTTP errors (4xx/5xx)
            log.warning(f"HTTP error {e.status} scraping {url}: {e.message}")
            # Don't raise RequestError here, just return None as the page failed
            return None
        except aiohttp.ClientError as e:
            # Handle other client errors (connection issues, etc.)
            log.warning(f"Client error scraping {url}: {e}")
            raise RequestError(f"Failed to fetch {url}: {e}") from e
        except Exception as e:
            # Catch unexpected errors during fetch
            log.error(f"Unexpected error fetching {url}: {e}")
            raise RequestError(f"Unexpected error fetching {url}: {e}") from e


    def _extract_emails_from_html(self, html_content: str, url: str) -> Set[str]:
        """Extracts emails from HTML content using BeautifulSoup and regex."""
        found_emails: Set[str] = set()
        if not html_content:
            return found_emails

        try:
            soup = BeautifulSoup(html_content, 'lxml') # Use lxml for speed

            # 1. Find mailto links
            for link in soup.select("a[href^='mailto:']"):
                href = link.get('href')
                if href:
                    email_part = href.split(':', 1)[1].split('?')[0].strip()
                    if email_part and self.settings.email_regex.match(email_part):
                        log.debug(f"Found via mailto link ({url}): {email_part}")
                        found_emails.add(email_part.lower())
                    elif email_part:
                         log.warning(f"Mailto content failed regex check: {email_part} from {url}")


            # 2. Extract emails from text content
            # Remove script/style tags to avoid extracting emails from code
            for element in soup(["script", "style"]):
                element.decompose()

            # Get text from the body or the whole document if body is not present
            body = soup.find('body')
            text_content = body.get_text(separator=' ', strip=True) if body else soup.get_text(separator=' ', strip=True)

            extracted_from_text = extract_emails_from_text(text_content, self.settings)
            if extracted_from_text:
                 log.debug(f"Found {len(extracted_from_text)} emails via regex in text ({url})")
                 found_emails.update(extracted_from_text) # Already lowercase and unique

            return found_emails

        except Exception as e:
            # Catch errors during parsing (e.g., complex/malformed HTML)
            log.error(f"Error parsing HTML content from {url}: {e}")
            raise HtmlParseError(f"Error parsing HTML from {url}: {e}") from e


    async def scrape_website_for_emails(self, base_url_str: str) -> List[str]:
        """
        Scrapes a website (starting URL + common pages) to find email addresses.

        Args:
            base_url_str: The starting URL or domain of the website to scrape.

        Returns:
            A list of unique, potentially valid email addresses found.

        Raises:
            RequestError: If there's a fundamental issue connecting or fetching URLs.
            HtmlParseError: If HTML parsing fails critically.
            UrlParseError: If the base_url_str is invalid.
        """
        start_time = asyncio.get_event_loop().time()
        log.info(f"Starting scrape for: {base_url_str}")

        try:
            # Normalize the base URL first
            normalized_base_url = normalize_url(base_url_str)
            base_parsed_url = urlparse(normalized_base_url)
            base_domain = base_parsed_url.netloc.removeprefix("www.")
        except Exception as e: # Catch UrlParseError or others from normalization
             log.error(f"Invalid base URL provided for scraping: {base_url_str} - {e}")
             # Re-raise or return empty list depending on desired strictness
             raise UrlParseError(f"Invalid base URL for scraping: {base_url_str}") from e


        all_found_emails: Set[str] = set()
        processed_urls: Set[str] = set()
        urls_to_visit: Set[str] = set()

        urls_to_visit.add(normalized_base_url)
        for page_path in self.settings.common_pages_to_scrape:
            try:
                # Ensure paths starting with / are joined correctly
                full_url = urljoin(normalized_base_url, page_path)
                parsed_full_url = urlparse(full_url)

                # Only scrape pages on the same base domain
                current_domain = parsed_full_url.netloc.removeprefix("www.")
                if current_domain == base_domain:
                    urls_to_visit.add(full_url)
                else:
                    log.debug(f"Skipping generated URL (different domain): {full_url}")
            except Exception as e:
                log.warning(f"Failed to join base URL {normalized_base_url} with page {page_path}: {e}")

        log.debug(f"Planning to scrape {len(urls_to_visit)} potential URLs.")

        successful_pages = 0
        failed_pages = 0
        any_page_successful = False

        # Process URLs one by one for now (can be parallelized later if needed)
        for page_url in urls_to_visit:
            if page_url in processed_urls:
                continue
            processed_urls.add(page_url)

            try:
                # Add slight delay between requests
                sleep_duration = self.settings.sleep_between_requests[0] # Use min sleep for now
                await asyncio.sleep(sleep_duration)

                html_content = await self._fetch_page(page_url)

                if html_content:
                    successful_pages += 1
                    any_page_successful = True
                    emails_on_page = self._extract_emails_from_html(html_content, page_url)
                    all_found_emails.update(emails_on_page)
                else:
                    failed_pages += 1 # Increment failed if fetch returned None

            except (RequestError, HtmlParseError) as e:
                # Log errors from fetch/parse but continue scraping other pages
                log.warning(f"Error processing page {page_url}: {e}")
                failed_pages += 1
            except Exception as e:
                # Catch any other unexpected errors during the loop for a single URL
                log.error(f"Unexpected error processing page {page_url}: {e}")
                failed_pages += 1


        if not any_page_successful and urls_to_visit:
            log.warning(f"Could not successfully scrape any pages for {normalized_base_url}")
            # Consider raising an error if no pages could be scraped at all
            # raise RequestError(f"Failed to scrape any pages for {normalized_base_url}")

        # Final filtering (optional, as regex check happens during extraction)
        # Example: filter out emails not matching the target domain if needed,
        # but the current logic extracts all valid emails found.
        final_emails = sorted(list(all_found_emails))

        elapsed = asyncio.get_event_loop().time() - start_time
        log.info(
            f"Scrape for {normalized_base_url} finished in {elapsed:.2f}s. "
            f"Attempted {len(processed_urls)} URLs ({successful_pages} successful, {failed_pages} failed). "
            f"Found {len(final_emails)} unique emails."
        )

        return final_emails

