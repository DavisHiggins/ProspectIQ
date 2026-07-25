"""Offline demo mode.

Runs the full pipeline — collection, normalization, enrichment, scoring,
export — against fictional records, making **no network requests** and
requiring no credentials.

Every profile below is invented. The domains use the RFC 2606 ``example.com``
reserved namespace, which can never resolve to a real host, and the names do not
refer to real people.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from rich.console import Console

from prospectiq.branding import (
    lead_table,
    print_info,
    print_section,
    print_success,
)
from prospectiq.constants import DEMO_OUTPUT_DIR
from prospectiq.enrichment.scoring import calculate_lead_score, score_email_candidate
from prospectiq.exporters import export_leads
from prospectiq.models import Lead

#: Fictional source records, shaped exactly as the real scrapers return them.
DEMO_RAW_PROFILES: list[dict[str, Any]] = [
    {
        "platform": "github",
        "username": "rivera-builds",
        "full_name": "Sam Rivera",
        "bio": "Founder at Northwind Labs. Building developer tooling. sam@northwind.example.com",
        "company": "Northwind Labs",
        "location": "Charlotte, NC",
        "website": "https://northwind.example.com",
        "follower_count": 8_420,
        "following_count": 180,
        "profile_url": "https://github.com/rivera-builds",
        "public_repos": 47,
    },
    {
        "platform": "linkedin",
        "username": "avery-chen-demo",
        "full_name": "Avery Chen",
        "headline": "Director of Operations at Ridgeline Supply",
        "bio": "Operations leader focused on logistics automation.",
        "website": "https://ridgeline.example.com",
        "profile_url": "https://www.linkedin.com/in/avery-chen-demo/",
        "is_verified": True,
    },
    {
        "platform": "instagram",
        "username": "themorganco",
        "full_name": "Morgan Ellis",
        "bio": "Brand consultant · Charlotte NC · hello@morganco.example.com · (704) 555-0142",
        "website": "https://morganco.example.com",
        "follower_count": 24_800,
        "following_count": 612,
        "profile_url": "https://www.instagram.com/themorganco/",
        "post_count": 318,
        "is_business": True,
    },
    {
        "platform": "linkbio",
        "username": "jaydencreates",
        "full_name": "Jayden Okafor",
        "bio": "Photographer and educator. Booking inquiries below.",
        "website": "https://jayden.example.com",
        "profile_url": "https://linktr.ee/jaydencreates",
        "provider": "linktree",
        "link_count": 6,
        "social_instagram": "jaydencreates",
        "social_youtube": "jaydencreates",
    },
    {
        "platform": "twitch",
        "username": "pixelforge",
        "full_name": "Pixel Forge Studio",
        "bio": "Live gamedev streams every Tuesday. Partnered.",
        "follower_count": 132_500,
        "profile_url": "https://twitch.tv/pixelforge",
        "is_partner": True,
    },
]

#: Pre-computed enrichment outcomes, so the demo shows realistic results without
#: touching DNS, SMTP, or any website.
DEMO_ENRICHMENT: dict[str, dict[str, Any]] = {
    "rivera-builds": {
        "email": "sam@northwind.example.com",
        "email_source": "bio",
        "company_domain": "northwind.example.com",
        "smtp_confirmed": True,
        "catch_all": False,
        "corroborating_emails": 2,
    },
    "avery-chen-demo": {
        "email": "avery.chen@ridgeline.example.com",
        "email_source": "pattern",
        "company": "Ridgeline Supply",
        "company_domain": "ridgeline.example.com",
        "smtp_confirmed": False,
        "catch_all": False,
        "corroborating_emails": 3,
    },
    "themorganco": {
        "email": "hello@morganco.example.com",
        "email_source": "bio",
        "phone": "(704) 555-0142",
        "company_domain": "morganco.example.com",
        "smtp_confirmed": True,
        "catch_all": True,
        "corroborating_emails": 1,
    },
    "jaydencreates": {
        "email": "bookings@jayden.example.com",
        "email_source": "bio_link",
        "company_domain": "jayden.example.com",
        "smtp_confirmed": False,
        "catch_all": False,
        "corroborating_emails": 1,
    },
    "pixelforge": {},
}

STAGE_PAUSE_SECONDS = 0.25


def build_demo_leads() -> list[Lead]:
    """Build the fully enriched demo lead set.

    Runs the real normalization and scoring code against fictional inputs, so
    the output reflects genuine pipeline behaviour rather than canned text.

    Returns:
        Five enriched, scored leads.
    """
    leads: list[Lead] = []

    for raw in DEMO_RAW_PROFILES:
        lead = Lead.from_raw(raw)
        _apply_demo_enrichment(lead)
        lead.lead_score = calculate_lead_score(lead)
        leads.append(lead)

    return leads


def _apply_demo_enrichment(lead: Lead) -> None:
    """Apply the stubbed enrichment outcome for one demo lead."""
    outcome = DEMO_ENRICHMENT.get(lead.username, {})
    if not outcome:
        return

    if outcome.get("phone"):
        lead.phone = outcome["phone"]
    if outcome.get("company"):
        lead.company = outcome["company"]
    if outcome.get("company_domain"):
        lead.company_domain = outcome["company_domain"]

    email = outcome.get("email")
    if not email:
        return

    lead.email = email
    lead.email_source = outcome["email_source"]
    lead.email_verified = bool(outcome["smtp_confirmed"]) and not outcome["catch_all"]
    lead.email_confidence = score_email_candidate(
        outcome["email_source"],
        smtp_confirmed=outcome["smtp_confirmed"],
        catch_all=outcome["catch_all"],
        corroborating_emails=outcome["corroborating_emails"],
    )


def run_demo(console: Console, output_dir: Path | None = None) -> Path:
    """Run the offline demo end to end and export a sample CSV.

    Takes no configuration: the demo must behave identically regardless of the
    user's environment, and it deliberately writes outside the normal export
    directory so fictional records never mix with collected ones.

    Args:
        console: The output console.
        output_dir: Where to write the sample CSV. Defaults to ``demo_output/``.

    Returns:
        The path of the exported CSV.
    """
    target_dir = output_dir or Path(DEMO_OUTPUT_DIR)

    print_section(console, "ProspectIQ demo", "offline · no credentials · no network requests")
    console.print()
    print_info(
        console,
        "Every profile below is fictional and uses reserved example.com domains.",
    )
    console.print()

    # -- Stage 1: collection ------------------------------------------------
    print_section(console, "1. Collection", f"{len(DEMO_RAW_PROFILES)} fictional source records")
    console.print()
    for raw in DEMO_RAW_PROFILES:
        print_success(
            console,
            f"[body]{raw['platform']}[/body] → @{raw['username']} "
            f"[muted]({raw.get('full_name', 'unknown')})[/muted]",
        )
        time.sleep(STAGE_PAUSE_SECONDS)

    # -- Stage 2: normalization --------------------------------------------
    leads = [Lead.from_raw(raw) for raw in DEMO_RAW_PROFILES]
    print_section(console, "2. Normalization", "source records → unified lead schema")
    console.print()
    print_info(
        console,
        f"Mapped {len(leads)} records from {len({lead.source for lead in leads})} sources "
        f"into one schema of {len(Lead.core_field_names())} fields.",
    )
    print_info(
        console,
        "Source-specific fields (public_repos, is_partner, social_*) are preserved "
        "as extra columns.",
    )

    # -- Stage 3: enrichment ------------------------------------------------
    print_section(console, "3. Enrichment", "website, company domain, and email inference")
    console.print()
    for lead in leads:
        _apply_demo_enrichment(lead)
        if lead.email:
            verdict = "SMTP confirmed" if lead.email_verified else "unconfirmed"
            print_success(
                console,
                f"@{lead.username} → [body]{lead.email}[/body] "
                f"[muted](via {lead.email_source}, {verdict})[/muted]",
            )
        else:
            print_info(console, f"@{lead.username} → no email candidate found")
        time.sleep(STAGE_PAUSE_SECONDS)

    # -- Stage 4: scoring ---------------------------------------------------
    print_section(console, "4. Scoring", "transparent, additive, 0-100")
    console.print()
    for lead in leads:
        lead.lead_score = calculate_lead_score(lead)
    console.print(lead_table(leads, title=""))

    # -- Stage 5: export ----------------------------------------------------
    print_section(console, "5. Export", "CSV with a stable column order")
    console.print()
    path = export_leads(leads, target_dir, source="demo")
    print_success(console, f"Wrote [body]{path}[/body] [muted]({len(leads)} leads)[/muted]")

    console.print()
    print_info(
        console,
        "That is the whole pipeline. A real run replaces stage 1 with live "
        "collection and stage 3 with actual DNS, HTTP, and SMTP lookups.",
    )
    console.print()

    return path
