import asyncio
import logging
import random
from typing import Optional, List, Set, Dict, Tuple
import aiohttp
from app.config import Settings
from app.models import EmailResult, FoundEmailData, ContactBase # Use ContactBase for input type hint
from app.core.dns_utils import DnsResolver, MailServer # Assuming DnsResolver is the class holding the aiodns resolver
from app.core.scraper import Scraper
from app.core.smtp_utils import SmtpVerifier
from app.core.patterns import generate_email_patterns
from app.exceptions import EmailSleuthError, DnsError # Import base errors

log = logging.getLogger(__name__)

# Define ValidatedContact structure internally or pass validated fields directly
# For simplicity here, find_email will accept validated fields.
# A separate validation step could create a ValidatedContact object if preferred.

class MailBeacon:
    def __init__(self, settings: Settings, http_session: aiohttp.ClientSession, dns_resolver: DnsResolver):
        """
        Initializes the MailBeacon orchestrator.

        Args:
            settings: The application settings instance.
            http_session: An initialized aiohttp ClientSession.
            dns_resolver: An initialized DnsResolver instance.
        """
        self.settings = settings
        self.http_client = http_session
        self.dns_resolver = dns_resolver
        self.scraper = Scraper(http_session, settings)
        self.smtp_verifier = SmtpVerifier(settings, dns_resolver) # Pass resolver to SmtpVerifier

    def is_generic_prefix(self, email: str) -> bool:
        """Checks if the local part of an email is in the generic prefixes list."""
        local_part = email.split('@')[0].lower()
        return local_part in self.settings.generic_email_prefixes

    async def find_email(
        self,
        first_name: str,
        last_name: str,
        domain: str, # Expects normalized domain
        website_url: str # Expects normalized URL
    ) -> EmailResult:
        """
        Finds and verifies email addresses for a given contact.
        Orchestrates pattern generation, scraping, scoring, and verification.

        Args:
            first_name: Validated first name.
            last_name: Validated last name.
            domain: Validated and normalized domain.
            website_url: Validated and normalized website URL.

        Returns:
            An EmailResult object containing the findings.

        Raises:
            EmailSleuthError or subclasses for critical failures during the process.
        """
        log.info(f"Finding email for: {first_name} {last_name}, Domain: {domain}, Website: {website_url}")
        start_time = asyncio.get_event_loop().time()

        results = EmailResult()
        first_lower = first_name.lower()
        last_lower = last_name.lower()

        # --- 1. Generate Patterns ---
        log.debug("Starting pattern generation...")
        generated_patterns = generate_email_patterns(first_name, last_name, domain, self.settings)
        if generated_patterns:
            results.methods_used.append("pattern_generation")
            log.debug(f"Finished pattern generation ({len(generated_patterns)} patterns).")

        # --- 2. Scrape Website ---
        log.debug("Starting website scraping...")
        scraped_emails: List[str] = []
        try:
            # Use website_url which should be normalized already
            scraped_emails_raw = await self.scraper.scrape_website_for_emails(website_url)
            # Filter scraped emails: must end with the target domain OR be generic (on any domain found)
            scraped_emails = [
                email for email in scraped_emails_raw
                if email.endswith(f"@{domain}") or self.is_generic_prefix(email)
            ]
            if scraped_emails:
                results.methods_used.append("website_scraping")
                log.info(f"Found {len(scraped_emails)} relevant emails via scraping.")
            log.debug("Finished website scraping.")
        except EmailSleuthError as e:
            log.warning(f"Website scraping failed for {website_url}: {e}. Proceeding without scraped emails.")
            # Store scraping error details? Maybe in verification_log?
            results.verification_log["scraping_error"] = f"Scraping failed: {e}"
        except Exception as e:
             log.error(f"Unexpected error during scraping for {website_url}: {e}. Proceeding without scraped emails.")
             results.verification_log["scraping_error"] = f"Unexpected scraping error: {e}"


        # --- 3. Combine and Order Candidates ---
        log.debug("Combining and ordering candidates...")
        all_candidates: List[str] = []
        seen_candidates: Set[str] = set()

        def add_candidate(email: str):
            email_lower = email.lower()
            if email_lower not in seen_candidates:
                seen_candidates.add(email_lower)
                all_candidates.append(email_lower) # Store lowercase

        # Prioritize candidates matching name parts
        name_candidates: List[str] = []
        other_candidates: List[str] = []

        for p in generated_patterns:
             lp = p.split('@')[0]
             if first_lower in lp or last_lower in lp:
                 name_candidates.append(p)
             else:
                 other_candidates.append(p)

        for s in scraped_emails:
             lp = s.split('@')[0]
             if first_lower in lp or last_lower in lp:
                 name_candidates.append(s)
             else:
                 other_candidates.append(s)

        # Add in prioritized order, ensuring uniqueness
        for email in name_candidates: add_candidate(email)
        for email in other_candidates: add_candidate(email)

        log.info(f"Total unique candidates to assess: {len(all_candidates)}")
        log.debug(f"Candidate list (ordered): {all_candidates}")

        # --- 4. Verify and Score Candidates ---
        log.debug("Starting candidate verification and scoring...")
        verified_emails_data: List[FoundEmailData] = []

        # Check mail server once (used by SmtpVerifier internally now)
        # mail_server = await self.smtp_verifier._get_mail_server(domain) # Check if needed here

        for email in all_candidates:
            if not self.settings.email_regex.match(email):
                log.warning(f"Skipping invalid candidate format: {email}")
                continue

            log.debug(f"Assessing candidate: {email}")
            confidence: int = 0 # Use int score 0-10
            verification_status: Optional[bool] = None
            verification_message: str = "Verification not attempted"
            is_catch_all_domain: bool = False # Track catch-all status

            email_local_part, email_domain_part = email.split('@', 1)
            is_scraped = email in scraped_emails # Check original list before lowercasing
            is_pattern = email in generated_patterns
            is_generic = self.is_generic_prefix(email)
            matches_primary_domain = (email_domain_part == domain)

            # Skip if not primary domain unless it's a scraped generic
            if not matches_primary_domain and not (is_scraped and is_generic):
                log.debug(f"Skipping candidate {email}: Non-primary domain ({email_domain_part}) and not a scraped generic.")
                continue

            name_in_email = first_lower in email_local_part or last_lower in email_local_part

            # --- Initial Confidence Scoring (similar to Rust) ---
            base_confidence = 0
            if is_pattern and name_in_email: base_confidence += 3
            if is_scraped and name_in_email: base_confidence += 5
            if is_scraped and not name_in_email: base_confidence += 2 # Scraped non-name gets some points
            if is_pattern and not name_in_email: base_confidence += 1 # Pattern non-name gets fewer
            if matches_primary_domain: base_confidence += 1

            log.debug(f"Base confidence for {email}: {base_confidence} (Scraped: {is_scraped}, Pattern: {is_pattern}, NameIn: {name_in_email}, Generic: {is_generic}, DomainMatch: {matches_primary_domain})")

            # Apply penalties for generic emails
            if is_generic:
                if name_in_email and base_confidence > 1:
                    penalty = 5
                    base_confidence = max(1, base_confidence - penalty)
                    log.debug(f"Applied penalty ({penalty}) for generic prefix '{email_local_part}'. New confidence: {base_confidence}")
                elif not name_in_email and base_confidence > 2:
                    penalty = 2
                    base_confidence = max(1, base_confidence - penalty)
                    log.debug(f"Applied smaller penalty ({penalty}) for scraped generic prefix '{email_local_part}'. New confidence: {base_confidence}")

            confidence = base_confidence

            # --- SMTP Verification ---
            # Decide if verification should be attempted
            # Verify if confidence is decent OR it was scraped and contains the name
            should_verify_smtp = confidence >= 3 or (is_scraped and name_in_email and confidence > 1)

            log.debug(f"Should verify {email}? {should_verify_smtp} (Confidence: {confidence})")

            smtp_start_time = asyncio.get_event_loop().time()
            if should_verify_smtp:
                if "smtp_verification" not in results.methods_used:
                    results.methods_used.append("smtp_verification")

                try:
                    # SmtpVerifier now handles retries internally
                    ver_status, ver_msg, is_catch_all = await self.smtp_verifier.verify_email_with_retries(email)
                    verification_status = ver_status
                    verification_message = ver_msg
                    is_catch_all_domain = is_catch_all # Store catch-all result

                    # Adjust confidence based on verification
                    if verification_status is True:
                        boost = 5
                        confidence += boost
                        log.debug(f"Applied boost ({boost}) for successful verification. New confidence: {confidence}")
                    elif verification_status is False:
                        confidence = 0 # Definitely doesn't exist
                        log.debug("Reset confidence to 0 due to failed verification.")
                    else: # Inconclusive
                        # Small boost for inconclusive, penalize more if catch-all suspected
                        boost = 0 if is_catch_all_domain else 1
                        confidence += boost
                        log.debug(f"Applied boost ({boost}) for inconclusive verification (CatchAll: {is_catch_all_domain}). New confidence: {confidence}")

                except EmailSleuthError as e:
                    log.warning(f"SMTP verification failed for {email}: {e}")
                    verification_status = None
                    verification_message = f"SMTP Error: {e}"
                    # Keep confidence as is, maybe slight penalty? For now, no change.
                except Exception as e:
                     log.error(f"Unexpected error during SMTP verification for {email}: {e}")
                     verification_status = None
                     verification_message = f"Unexpected SMTP Error: {e}"

            else:
                # Log why verification was skipped
                # Check if DNS failed previously (this check might be better placed before the loop)
                # mail_server_available = await self.smtp_verifier._get_mail_server(domain) is not None # Re-check or store status
                # if not mail_server_available:
                #      verification_message = "Verification skipped (DNS lookup failed)"
                # else:
                verification_message = "Verification skipped (low initial confidence)"

            smtp_duration_secs = asyncio.get_event_loop().time() - smtp_start_time
            results.verification_log[email] = f"{verification_message} (Took {smtp_duration_secs:.2f}s)"

            # Clamp confidence score 0-10
            final_confidence = max(0, min(10, confidence))

            if final_confidence > 0:
                log.debug(f"Storing final data for {email}: Confidence={final_confidence}, Status={verification_status}")
                verified_emails_data.append(FoundEmailData(
                    email=email,
                    confidence=final_confidence,
                    source="scraped" if is_scraped else "pattern",
                    is_generic=is_generic,
                    verification_status=verification_status,
                    verification_message=verification_message, # Store the final message
                ))
            else:
                log.debug(f"Discarding candidate {email} due to zero final confidence.")

            # Sleep after verification attempt (if performed)
            if should_verify_smtp:
                 min_sleep, max_sleep = self.settings.sleep_between_requests
                 # Add adaptive delay based on SMTP time? Maybe later.
                 sleep_duration = random.uniform(min_sleep, max_sleep) if max_sleep > min_sleep else min_sleep
                 log.debug(f"Sleeping {sleep_duration:.2f}s after verification attempt for {email}")
                 await asyncio.sleep(sleep_duration)


        # --- 5. Select Best Email ---
        log.debug("Sorting verified email data...")
        verified_emails_data.sort(
            key=lambda e: (e.confidence, not e.is_generic, e.source == 'scraped'), # Confidence desc, Non-generic first, Scraped preferred
            reverse=True
        )
        results.found_emails = verified_emails_data
        log.debug(f"Sorted results: {[e.email for e in results.found_emails]}")

        results.most_likely_email = None
        results.confidence_score = 0

        # Find best non-generic above threshold
        best_non_generic = next((e for e in results.found_emails if not e.is_generic and e.confidence >= self.settings.confidence_threshold), None)

        if best_non_generic:
            results.most_likely_email = best_non_generic.email
            results.confidence_score = best_non_generic.confidence
            log.info(f"Selected best non-generic: {best_non_generic.email} (Conf: {best_non_generic.confidence})")
        else:
            # If no non-generic found, consider the top candidate overall
            if results.found_emails:
                top_candidate = results.found_emails[0]
                # Select if confidence is high enough
                # Allow generic only if confidence meets the higher generic threshold
                if top_candidate.confidence >= self.settings.confidence_threshold and \
                   (not top_candidate.is_generic or top_candidate.confidence >= self.settings.generic_confidence_threshold):
                        results.most_likely_email = top_candidate.email
                        results.confidence_score = top_candidate.confidence
                        log.info(f"Selected top candidate ({'generic' if top_candidate.is_generic else 'non-generic'}): {top_candidate.email} (Conf: {top_candidate.confidence})")
                else:
                     log.info(f"Top candidate '{top_candidate.email}' confidence ({top_candidate.confidence}) or type (Generic: {top_candidate.is_generic}) did not meet threshold(s). No email selected.")
            else:
                 log.info("No candidates found with confidence > 0.")


        total_duration = asyncio.get_event_loop().time() - start_time
        log.info(f"Finished finding email for: {first_name} {last_name}. Result: {results.most_likely_email}. Duration: {total_duration:.2f}s")

        return results
