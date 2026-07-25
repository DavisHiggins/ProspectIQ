"""SMTP-level existence checks for email candidates.

The check opens an SMTP conversation and issues ``RCPT TO`` without ever sending
a message, then disconnects. No mail is delivered and no content is transmitted.

This is inherently unreliable: many providers accept every recipient
(catch-all), greylist unknown senders, or block verification traffic outright.
Results are therefore reported as *unconfirmed* rather than *invalid*, and a
catch-all domain is flagged so its acceptance is not mistaken for proof.
"""

from __future__ import annotations

import smtplib
import socket
from dataclasses import dataclass

from prospectiq.constants import SMTP_HELO_HOST, SMTP_MAIL_FROM, SMTP_TIMEOUT
from prospectiq.logging_config import get_logger

logger = get_logger(__name__)

SMTP_PORT = 25
SMTP_OK = 250

#: Address used to probe whether a domain accepts mail for anything at all.
_CATCH_ALL_PROBE = "zzz-prospectiq-nonexistent-999"


@dataclass(frozen=True)
class VerificationResult:
    """Outcome of an SMTP existence check.

    Attributes:
        confirmed: The server explicitly accepted this address.
        catch_all: The server accepts any address on the domain, so
            ``confirmed`` carries little information.
        checked: Whether the check actually ran. ``False`` means the result is
            unknown, not negative.
        detail: Human-readable explanation, for verbose logging.
    """

    confirmed: bool = False
    catch_all: bool = False
    checked: bool = False
    detail: str = "not checked"


def resolve_mx(domain: str) -> str:
    """Return the lowest-preference MX host for a domain, or an empty string."""
    if not domain:
        return ""
    try:
        import dns.resolver
    except ImportError:
        logger.debug("dnspython is not installed; skipping MX lookup")
        return ""

    try:
        records = dns.resolver.resolve(domain, "MX")
    except Exception as exc:
        logger.debug("No MX records for %s: %s", domain, exc)
        return ""

    try:
        best = min(records, key=lambda r: r.preference)
    except (ValueError, AttributeError):
        return ""

    return str(best.exchange).rstrip(".")


def domain_accepts_mail(domain: str) -> bool:
    """Whether a domain publishes MX records at all."""
    return bool(resolve_mx(domain))


def verify_email(email: str, *, enabled: bool = True) -> VerificationResult:
    """Check whether a mail server accepts an address.

    Args:
        email: The address to check.
        enabled: When ``False``, returns an unchecked result immediately. Lets
            callers honour ``PROSPECTIQ_SMTP_VERIFY=false`` without branching.

    Returns:
        A :class:`VerificationResult`. ``confirmed=False`` always means
        "unconfirmed", never "this address is invalid".
    """
    if not enabled:
        return VerificationResult(detail="SMTP verification disabled")

    _, _, domain = email.partition("@")
    if not domain:
        return VerificationResult(detail="malformed address")

    mx_host = resolve_mx(domain)
    if not mx_host:
        return VerificationResult(detail=f"no MX records for {domain}")

    try:
        with smtplib.SMTP(timeout=SMTP_TIMEOUT) as smtp:
            smtp.connect(mx_host, SMTP_PORT)
            smtp.helo(SMTP_HELO_HOST)
            smtp.mail(SMTP_MAIL_FROM)

            code, _ = smtp.rcpt(email)
            confirmed = code == SMTP_OK

            # If the server also accepts an address that cannot exist, its
            # acceptance of the real one proves nothing.
            probe_code, _ = smtp.rcpt(f"{_CATCH_ALL_PROBE}@{domain}")
            catch_all = probe_code == SMTP_OK

            return VerificationResult(
                confirmed=confirmed and not catch_all,
                catch_all=catch_all,
                checked=True,
                detail=f"server responded {code}" + (" (catch-all)" if catch_all else ""),
            )

    except (
        TimeoutError,
        smtplib.SMTPException,
        socket.gaierror,
        ConnectionRefusedError,
        OSError,
    ) as exc:
        logger.debug("SMTP check unavailable for %s: %s", email, exc)
        return VerificationResult(detail=f"server did not permit verification: {exc}")
