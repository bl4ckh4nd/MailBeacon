import asyncio
import logging
import random
import string
from typing import Optional, Tuple
import aiosmtplib
from app.config import Settings
from app.exceptions import (
    SmtpError, SmtpCommandError, SmtpTlsError,
    SmtpTemporaryFailureError, SmtpPermanentFailureError, SmtpInconclusiveError,
    ConfigError
)
from app.core.dns_utils import resolve_mail_server, MailServer, create_resolver # Need DNS lookup

log = logging.getLogger(__name__)

class SmtpVerificationResultInternal:
    """Internal representation of SMTP verification outcome."""
    def __init__(self, exists: Optional[bool], message: str, should_retry: bool, is_catch_all: bool = False):
        self.exists = exists
        self.message = message
        self.should_retry = should_retry
        self.is_catch_all = is_catch_all

    @classmethod
    def conclusive(cls, exists: bool, message: str, is_catch_all: bool = False):
        return cls(exists=exists, message=message, should_retry=False, is_catch_all=is_catch_all)

    @classmethod
    def inconclusive_retry(cls, message: str, is_catch_all: bool = False):
        return cls(exists=None, message=message, should_retry=True, is_catch_all=is_catch_all)

    @classmethod
    def inconclusive_no_retry(cls, message: str, is_catch_all: bool = False):
        return cls(exists=None, message=message, should_retry=False, is_catch_all=is_catch_all)


class SmtpVerifier:
    def __init__(self, settings: Settings, dns_resolver: aiosmtplib.DNSResolver):
        """
        Initializes the SmtpVerifier.

        Args:
            settings: The application settings instance.
            dns_resolver: An initialized aiodns resolver instance.
        """
        self.settings = settings
        self.dns_resolver = dns_resolver
        try:
            # Validate sender email format during initialization
            aiosmtplib.email.parse_address(self.settings.smtp_sender_email)
        except ValueError as e:
            raise ConfigError(f"Invalid smtp_sender_email in config: {self.settings.smtp_sender_email} - {e}") from e

    async def _get_mail_server(self, domain: str) -> Optional[MailServer]:
        """Resolves the mail server for the domain."""
        try:
            mail_server = await resolve_mail_server(self.dns_resolver, domain, self.settings)
            log.info(f"Using mail server {mail_server.exchange} (Pref: {mail_server.preference}) for domain {domain}")
            return mail_server
        except (SmtpError, DnsError) as e: # Catch DNS errors specifically
            log.warning(f"Failed to resolve mail server for {domain}: {e}. SMTP verification will be skipped.")
            return None

    def _generate_random_local_part(self, length=12):
        """Generates a random string for catch-all detection."""
        chars = string.ascii_lowercase + string.digits
        return ''.join(random.choice(chars) for _ in range(length))

    async def _verify_single_attempt(
        self,
        email: str,
        domain: str,
        mail_server: MailServer
    ) -> SmtpVerificationResultInternal:
        """Performs a single SMTP RCPT TO check attempt."""
        log.debug(f"Starting SMTP check for {email} via {mail_server.exchange} (Domain: {domain})")

        smtp_client = None
        try:
            # Validate recipient format before connecting
            try:
                 aiosmtplib.email.parse_address(email)
            except ValueError:
                 log.warning(f"Invalid recipient email format: {email}")
                 return SmtpVerificationResultInternal.conclusive(False, "Invalid email format")

            smtp_client = aiosmtplib.SMTP(
                hostname=mail_server.exchange,
                port=25, # Standard SMTP port
                timeout=self.settings.smtp_timeout,
                # source_address= # Can be added if needed
            )
            await smtp_client.connect(timeout=self.settings.smtp_timeout)
            log.debug(f"Connected to {mail_server.exchange}:25")

            # Send EHLO/HELO
            # Use localhost as default HELO domain, can be configured if needed
            helo_domain = "localhost"
            await smtp_client.ehlo(hostname=helo_domain) # Try EHLO first
            log.debug(f"EHLO {helo_domain} successful")

            # Check for STARTTLS support and initiate if available/required (optional enhancement)
            # if smtp_client.supports_extension("starttls"):
            #     log.debug("Server supports STARTTLS, attempting upgrade...")
            #     try:
            #         await smtp_client.starttls(timeout=self.settings.smtp_timeout)
            #         log.debug("STARTTLS successful")
            #         # Re-issue EHLO after STARTTLS
            #         await smtp_client.ehlo(hostname=helo_domain)
            #     except aiosmtplib.SMTPException as e:
            #         log.warning(f"STARTTLS failed: {e}. Proceeding without TLS.")
            #         # Decide if TLS is mandatory based on server response or config

            # MAIL FROM
            log.debug(f"Sending MAIL FROM:<{self.settings.smtp_sender_email}>")
            code, msg = await smtp_client.mail(self.settings.smtp_sender_email)
            if code >= 400:
                log.error(f"MAIL FROM <{self.settings.smtp_sender_email}> rejected by {mail_server.exchange}: {code} {msg}")
                # Check for specific errors like STARTTLS required
                if "starttls" in msg.lower() or ("530" in str(code) and "5.7.0" in msg.lower()):
                     return SmtpVerificationResultInternal.inconclusive_retry(f"Server requires STARTTLS: {code} {msg}")
                return SmtpVerificationResultInternal.inconclusive_no_retry(f"MAIL FROM rejected: {code} {msg}")
            log.debug(f"MAIL FROM accepted: {code} {msg}")

            # RCPT TO (Target Email)
            log.debug(f"Sending RCPT TO:<{email}>")
            target_code, target_msg = await smtp_client.rcpt(email)
            log.info(f"RCPT TO:<{email}> result: Code={target_code}, Msg='{target_msg}'")

            # Basic Catch-All Detection (if target email was accepted)
            is_catch_all = False
            if target_code < 400: # If target email was accepted
                random_local = self._generate_random_local_part()
                random_email = f"{random_local}@{domain}"
                log.debug(f"Checking for catch-all with: RCPT TO:<{random_email}>")
                try:
                    catch_all_code, catch_all_msg = await smtp_client.rcpt(random_email)
                    if catch_all_code < 400:
                        is_catch_all = True
                        log.warning(f"Domain {domain} appears to be a catch-all (accepted random user {random_email} with code {catch_all_code})")
                    else:
                         log.debug(f"Catch-all check negative (random user rejected with code {catch_all_code})")
                except aiosmtplib.SMTPResponseException as e:
                     log.debug(f"Catch-all check negative (random user rejected with code {e.code})")
                except Exception as e:
                    log.warning(f"Error during catch-all RCPT TO check (ignoring): {e}")


            # Interpret RCPT TO result
            if target_code < 300: # 2xx codes - Success
                if is_catch_all:
                    return SmtpVerificationResultInternal.inconclusive_retry(
                        f"SMTP accepted (Possible Catch-All): {target_code} {target_msg}", is_catch_all=True
                    )
                else:
                    return SmtpVerificationResultInternal.conclusive(
                        True, f"SMTP Verification OK: {target_code} {target_msg}", is_catch_all=False
                    )
            elif 300 <= target_code < 400: # 3xx - Unexpected intermediate
                 return SmtpVerificationResultInternal.inconclusive_retry(
                     f"SMTP Unexpected Intermediate Code: {target_code} {target_msg}"
                 )
            elif 400 <= target_code < 500: # 4xx - Transient Negative
                return SmtpVerificationResultInternal.inconclusive_retry(
                    f"SMTP Temp Failure/Greylisted? (4xx): {target_code} {target_msg}"
                )
            else: # 5xx - Permanent Negative
                rejection_phrases = [
                    "unknown", "no such", "unavailable", "rejected", "doesn't exist",
                    "disabled", "invalid address", "recipient not found", "user unknown",
                    "mailbox unavailable", "no mailbox",
                ]
                msg_lower = target_msg.lower()
                is_user_unknown = str(target_code) in ["550", "551", "553"] or \
                                  any(p in msg_lower for p in rejection_phrases)

                if is_user_unknown:
                    return SmtpVerificationResultInternal.conclusive(
                        False, f"SMTP Rejected (User Likely Unknown): {target_code} {target_msg}"
                    )
                else:
                    # Other 5xx errors might be policy, server issues, etc. Treat as permanent failure but maybe retry once?
                    # For simplicity now, treat all 5xx as non-existent for the API result.
                     return SmtpVerificationResultInternal.conclusive(
                        False, f"SMTP Rejected (Policy/Other 5xx): {target_code} {target_msg}"
                    )

        except aiosmtplib.SMTPConnectError as e:
            log.warning(f"SMTP connection failed for {mail_server.exchange}: {e}")
            # Check for common blocking indicators
            err_str = str(e).lower()
            if "timed out" in err_str or "connection refused" in err_str:
                 log.error(f"Port 25 to {mail_server.exchange} appears blocked. Check firewall/ISP.")
                 # Don't retry if connection is fundamentally blocked
                 return SmtpVerificationResultInternal.inconclusive_no_retry(f"Connection failed (likely blocked): {e}")
            return SmtpVerificationResultInternal.inconclusive_retry(f"Connection failed: {e}")
        except aiosmtplib.SMTPHeloError as e:
            log.warning(f"SMTP HELO/EHLO failed for {mail_server.exchange}: {e.code} {e.message}")
            return SmtpVerificationResultInternal.inconclusive_retry(f"HELO/EHLO failed: {e.code} {e.message}")
        except aiosmtplib.SMTPResponseException as e:
            log.warning(f"SMTP Response Error for {email} via {mail_server.exchange}: {e.code} {e.message}")
            # Map specific response errors if needed, otherwise treat as inconclusive retry
            if 400 <= e.code < 500:
                 return SmtpVerificationResultInternal.inconclusive_retry(f"SMTP Temp Failure (4xx): {e.code} {e.message}")
            elif e.code >= 500:
                 # Could be permanent, but might warrant one retry
                 return SmtpVerificationResultInternal.inconclusive_retry(f"SMTP Perm Failure? (5xx): {e.code} {e.message}")
            else:
                 return SmtpVerificationResultInternal.inconclusive_retry(f"SMTP Response Error: {e.code} {e.message}")
        except asyncio.TimeoutError:
             log.warning(f"SMTP operation timed out for {email} via {mail_server.exchange}")
             return SmtpVerificationResultInternal.inconclusive_retry("SMTP operation timed out")
        except OSError as e:
             # Catch potential socket errors not covered by aiosmtplib exceptions
             log.error(f"Socket error during SMTP check for {email} via {mail_server.exchange}: {e}")
             return SmtpVerificationResultInternal.inconclusive_retry(f"Socket error: {e}")
        except Exception as e:
            log.error(f"Unexpected error during SMTP check for {email} via {mail_server.exchange}: {e}")
            # Raise a specific SmtpError for unexpected issues
            raise SmtpError(f"Unexpected SMTP error: {e}") from e
        finally:
            if smtp_client and smtp_client.is_connected:
                try:
                    await smtp_client.quit(timeout=2) # Short timeout for quit
                except (aiosmtplib.SMTPException, asyncio.TimeoutError, OSError):
                    # Ignore errors during quit
                    pass
                except Exception as e:
                     log.warning(f"Ignoring unexpected error during SMTP quit: {e}")


    async def verify_email_with_retries(self, email: str) -> Tuple[Optional[bool], str, bool]:
        """
        Verifies an email using SMTP with retries for inconclusive results.

        Args:
            email: The email address to verify.

        Returns:
            Tuple (exists: Optional[bool], message: str, is_catch_all: bool)
        """
        domain = email.split('@')[-1]
        mail_server = await self._get_mail_server(domain)

        if not mail_server:
            return None, "SMTP check skipped (DNS lookup failed)", False

        last_result: Optional[bool] = None
        last_message = "SMTP check did not run or complete"
        is_catch_all = False

        for attempt in range(self.settings.max_verification_attempts):
            log.info(f"Attempt {attempt + 1}/{self.settings.max_verification_attempts} SMTP check for {email} via {mail_server.exchange}")
            try:
                result = await self._verify_single_attempt(email, domain, mail_server)
                last_result = result.exists
                last_message = result.message
                is_catch_all = result.is_catch_all # Update catch-all status

                if result.exists is not None:
                    log.debug(f"SMTP check conclusive (Result: {result.exists}) on attempt {attempt + 1}.")
                    break # Stop on conclusive result

                if not result.should_retry:
                    log.warning(f"SMTP check failed with non-retriable status on attempt {attempt + 1}. Stopping. Msg: {result.message}")
                    break # Stop if retry is not advised

                log.warning(f"SMTP check inconclusive on attempt {attempt + 1}. Message: {result.message}")

            except SmtpError as e: # Catch unexpected errors from _verify_single_attempt
                log.error(f"Unexpected SmtpError during attempt {attempt + 1}: {e}")
                last_message = f"Internal error during SMTP check: {e}"
                # Decide if this specific error warrants stopping retries
                break # Stop on unexpected internal errors
            except Exception as e:
                 log.error(f"Critical unexpected error during attempt {attempt + 1}: {e}")
                 last_message = f"Critical internal error during SMTP check: {e}"
                 break # Stop on critical errors


            # Sleep only if there are more attempts and the result was inconclusive
            if attempt < self.settings.max_verification_attempts - 1 and last_result is None:
                # Use configured sleep range
                min_sleep, max_sleep = self.settings.sleep_between_requests
                sleep_duration = random.uniform(min_sleep, max_sleep) if max_sleep > min_sleep else min_sleep
                log.debug(f"Sleeping {sleep_duration:.2f}s before next SMTP attempt.")
                await asyncio.sleep(sleep_duration)

        log.info(f"Final SMTP verification result for {email}: Status={last_result}, Msg='{last_message}', CatchAll={is_catch_all}")
        return last_result, last_message, is_catch_all
