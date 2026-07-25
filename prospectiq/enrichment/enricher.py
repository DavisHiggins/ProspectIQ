"""The enrichment pipeline.

Takes a normalized :class:`~prospectiq.models.Lead` and fills in what the source
profile did not provide: contact details from the lead's own website, the
company domain behind a stated employer, and a scored best-guess email address.

Every stage is optional and failure-tolerant. Enrichment must never lose a lead
that was collected successfully, so an unreachable website or a mail server that
refuses verification degrades the result rather than discarding it.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from prospectiq.config import Config
from prospectiq.constants import (
    CONTACT_PAGE_PATHS,
    NON_COMPANY_DOMAINS,
)
from prospectiq.enrichment.email_patterns import (
    ROLE_ADDRESSES,
    extract_domain,
    generate_candidates,
    infer_from_observed,
    split_name,
)
from prospectiq.enrichment.scoring import calculate_lead_score, score_email_candidate
from prospectiq.enrichment.smtp_verify import domain_accepts_mail, verify_email
from prospectiq.logging_config import get_logger
from prospectiq.models import Lead
from prospectiq.utilities.net import httpx_proxy, polite_delay, random_user_agent
from prospectiq.utilities.text import extract_emails, extract_phone, extract_urls

logger = get_logger(__name__)

PAGE_TIMEOUT = 10.0
MAX_BIO_LINKS = 3
MAX_SMTP_GUESSES = 4
INTER_PAGE_DELAY = (0.3, 0.8)

#: Company-name suffixes stripped before guessing a domain.
_LEGAL_SUFFIXES = (" inc", " llc", " ltd", " co", " corp", " group", " holdings")

#: TLDs tried when resolving a company name to a domain.
_DOMAIN_GUESS_TLDS = (".com", ".io", ".co")


@dataclass
class EmailCandidate:
    """An email address under consideration, with its provenance."""

    address: str
    source: str


class LeadEnricher:
    """Enriches leads with contact details, company data, and scores.

    One instance may be reused across a whole run; it caches per-domain lookups
    so a batch of leads at the same company does not repeat DNS and HTTP work.

    Args:
        config: Runtime configuration.
        hunter_api_key: Optional Hunter.io key. Defaults to the configured one.
    """

    def __init__(self, config: Config, hunter_api_key: str | None = None) -> None:
        self.config = config
        self.hunter_api_key = (
            hunter_api_key if hunter_api_key is not None else config.hunter_api_key
        )
        self._page_cache: dict[str, str] = {}
        self._domain_cache: dict[str, str] = {}
        self._client = httpx.Client(
            timeout=PAGE_TIMEOUT,
            follow_redirects=True,
            proxy=httpx_proxy(config),
        )

    def __enter__(self) -> LeadEnricher:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def close(self) -> None:
        """Release the HTTP client."""
        self._client.close()

    # -- public API --------------------------------------------------------

    def enrich(self, lead: Lead) -> Lead:
        """Enrich a lead in place and return it.

        The lead is always returned, scored, even when every enrichment stage
        finds nothing.
        """
        candidates: list[EmailCandidate] = []
        observed_emails: list[str] = []

        self._from_biography(lead, candidates)
        observed_emails += self._from_website(lead, candidates)
        observed_emails += self._from_company_domain(lead, candidates)
        self._from_bio_links(lead, candidates)

        work_domain = lead.company_domain or extract_domain(lead.website)
        if work_domain and not _is_social(work_domain):
            self._from_pattern(lead, work_domain, observed_emails, candidates)
            if not candidates:
                self._from_smtp_guess(lead, work_domain, candidates)
            self._from_hunter(lead, work_domain, candidates)

        self._select_best_email(lead, candidates, len(observed_emails))
        lead.lead_score = calculate_lead_score(lead)
        return lead

    def enrich_all(self, leads: list[Lead]) -> list[Lead]:
        """Enrich a batch of leads sequentially.

        Sequential by design: parallel enrichment would multiply the request
        rate against the same third-party sites.
        """
        return [self.enrich(lead) for lead in leads]

    # -- stages ------------------------------------------------------------

    def _from_biography(self, lead: Lead, candidates: list[EmailCandidate]) -> None:
        """Harvest contact details the lead published in their own bio."""
        if not lead.biography:
            return

        for email in extract_emails(lead.biography):
            candidates.append(EmailCandidate(email, "bio"))

        if not lead.phone:
            lead.phone = extract_phone(lead.biography)

    def _from_website(self, lead: Lead, candidates: list[EmailCandidate]) -> list[str]:
        """Deep-scrape the lead's own website for contact details."""
        if not lead.website or _is_social(lead.website):
            return []

        found = self._scrape_contact_pages(lead.website)
        if found.emails:
            candidates.append(EmailCandidate(found.emails[0], "website"))
        if found.phone and not lead.phone:
            lead.phone = found.phone
        return found.emails

    def _from_company_domain(self, lead: Lead, candidates: list[EmailCandidate]) -> list[str]:
        """Resolve the stated employer to a domain and scrape it."""
        if lead.company_domain:
            return []

        domain = self._resolve_company_domain(lead)
        if not domain:
            return []

        lead.company_domain = domain

        # Only scrape the company site when the lead has no site of their own.
        if lead.website and not _is_social(lead.website):
            return []

        found = self._scrape_contact_pages(f"https://{domain}")
        if found.emails:
            candidates.append(EmailCandidate(found.emails[0], "website"))
        if found.phone and not lead.phone:
            lead.phone = found.phone
        return found.emails

    def _from_bio_links(self, lead: Lead, candidates: list[EmailCandidate]) -> None:
        """Follow links published in the bio, e.g. a link-in-bio page."""
        if not lead.biography:
            return

        for url in extract_urls(lead.biography)[:MAX_BIO_LINKS]:
            html = self._fetch(url)
            if not html:
                continue
            emails = extract_emails(html)
            if emails:
                candidates.append(EmailCandidate(emails[0], "bio_link"))
            if not lead.phone:
                lead.phone = extract_phone(html)

    def _from_pattern(
        self,
        lead: Lead,
        domain: str,
        observed: list[str],
        candidates: list[EmailCandidate],
    ) -> None:
        """Infer the lead's address from the company's email house style."""
        if not lead.display_name or not observed:
            return
        inferred = infer_from_observed(lead.display_name, domain, observed)
        if inferred:
            candidates.append(EmailCandidate(inferred, "pattern"))

    def _from_smtp_guess(self, lead: Lead, domain: str, candidates: list[EmailCandidate]) -> None:
        """Probe a few likely addresses when nothing else was found.

        Only runs as a last resort, is capped at a handful of probes, and stops
        at the first confirmation.
        """
        if not self.config.smtp_verify or not lead.display_name:
            return
        if not domain_accepts_mail(domain):
            return

        for candidate in generate_candidates(lead.display_name, domain)[:MAX_SMTP_GUESSES]:
            result = verify_email(candidate, enabled=True)
            if result.confirmed:
                candidates.append(EmailCandidate(candidate, "smtp_guess"))
                return

    def _from_hunter(self, lead: Lead, domain: str, candidates: list[EmailCandidate]) -> None:
        """Query Hunter.io, when the user supplied an API key."""
        if not self.hunter_api_key or not lead.display_name:
            return

        first, last = split_name(lead.display_name)
        if not (first and last):
            return

        try:
            response = self._client.get(
                "https://api.hunter.io/v2/email-finder",
                params={
                    "domain": domain,
                    "first_name": first,
                    "last_name": last,
                    "api_key": self.hunter_api_key,
                },
            )
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.debug("Hunter.io lookup failed for %s: %s", domain, exc)
            return

        email = (payload.get("data") or {}).get("email")
        if email:
            candidates.append(EmailCandidate(email, "hunter.io"))

    # -- selection ---------------------------------------------------------

    def _select_best_email(
        self, lead: Lead, candidates: list[EmailCandidate], observed_count: int
    ) -> None:
        """Score every candidate and record the strongest on the lead."""
        if not candidates:
            return

        seen: set[str] = set()
        best_score = -1
        best: tuple[EmailCandidate, bool] | None = None

        for candidate in candidates:
            key = candidate.address.lower()
            if key in seen:
                continue
            seen.add(key)

            verification = verify_email(candidate.address, enabled=self.config.smtp_verify)
            score = score_email_candidate(
                candidate.source,
                smtp_confirmed=verification.confirmed,
                catch_all=verification.catch_all,
                corroborating_emails=observed_count,
            )
            if score > best_score:
                best_score = score
                best = (candidate, verification.confirmed)

        if best is None:
            return

        candidate, confirmed = best
        lead.email = candidate.address
        lead.email_confidence = best_score
        lead.email_source = candidate.source
        lead.email_verified = confirmed

    # -- helpers -----------------------------------------------------------

    def _resolve_company_domain(self, lead: Lead) -> str:
        """Find a live domain for the lead's employer via DNS MX lookup."""
        names = _company_name_candidates(lead)
        for name in names[:3]:
            if name in self._domain_cache:
                if self._domain_cache[name]:
                    return self._domain_cache[name]
                continue

            resolved = ""
            slug = "".join(ch for ch in name.lower() if ch.isalnum())
            if slug:
                for tld in _DOMAIN_GUESS_TLDS:
                    if domain_accepts_mail(f"{slug}{tld}"):
                        resolved = f"{slug}{tld}"
                        break

            self._domain_cache[name] = resolved
            if resolved:
                return resolved

        return ""

    def _scrape_contact_pages(self, website: str) -> PageFindings:
        """Fetch a site's home, contact, and about pages for contact details."""
        base = website.rstrip("/")
        if not base.startswith(("http://", "https://")):
            base = f"https://{base}"

        emails: list[str] = []
        phone = ""

        for index, path in enumerate(CONTACT_PAGE_PATHS):
            html = self._fetch(f"{base}{path}")
            if html:
                emails.extend(e for e in extract_emails(html) if e not in emails)
                if not phone:
                    phone = extract_phone(html)

            # Stop early once we have a personal address and a phone number.
            if phone and any(not _is_role_address(e) for e in emails):
                break

            if index < len(CONTACT_PAGE_PATHS) - 1:
                polite_delay(INTER_PAGE_DELAY)

        # Prefer a person's address over a generic role mailbox.
        emails.sort(key=_is_role_address)
        return PageFindings(emails=emails, phone=phone)

    def _fetch(self, url: str) -> str:
        """GET a page, returning its body or an empty string on any failure."""
        if url in self._page_cache:
            return self._page_cache[url]

        body = ""
        try:
            response = self._client.get(url, headers={"User-Agent": random_user_agent()})
            if response.status_code == 200:
                body = response.text
        except httpx.HTTPError as exc:
            logger.debug("Could not fetch %s: %s", url, exc)

        self._page_cache[url] = body
        return body


@dataclass
class PageFindings:
    """Contact details harvested from one or more pages."""

    emails: list[str]
    phone: str


def _is_social(url: str) -> bool:
    """Whether a URL points at a social profile rather than a real website."""
    lowered = url.lower()
    return any(domain in lowered for domain in NON_COMPANY_DOMAINS)


def _is_role_address(email: str) -> bool:
    """Whether an address is a generic mailbox rather than a person's."""
    local = email.split("@")[0].lower()
    return local in ROLE_ADDRESSES or local in {"support", "sales", "admin", "team"}


def _company_name_candidates(lead: Lead) -> list[str]:
    """Extract plausible employer names from a lead's company and headline."""
    names: list[str] = []

    if lead.company:
        names.append(lead.company)

    # Headlines are conventionally "Role at Company".
    for marker in (" at ", " @ ", " | "):
        if marker in lead.headline:
            tail = lead.headline.split(marker)[-1].strip().rstrip(".")
            if tail:
                names.append(tail)

    cleaned: list[str] = []
    seen: set[str] = set()
    for name in names:
        value = name.strip()
        for suffix in _LEGAL_SUFFIXES:
            if value.lower().endswith(suffix):
                value = value[: -len(suffix)].strip()
        value = value.strip(" .,-")
        if len(value) > 2 and value.lower() not in seen:
            seen.add(value.lower())
            cleaned.append(value)

    return cleaned


def enrich_lead(lead: Lead, config: Config) -> Lead:
    """Enrich a single lead. Convenience wrapper around :class:`LeadEnricher`."""
    with LeadEnricher(config) as enricher:
        return enricher.enrich(lead)
