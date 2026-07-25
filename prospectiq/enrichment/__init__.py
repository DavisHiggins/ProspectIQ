"""Contact enrichment, email inference, verification, and scoring."""

from prospectiq.enrichment.email_patterns import (
    apply_pattern,
    detect_pattern,
    extract_domain,
    generate_candidates,
    infer_from_observed,
    split_name,
)
from prospectiq.enrichment.enricher import LeadEnricher, enrich_lead
from prospectiq.enrichment.scoring import calculate_lead_score, score_email_candidate
from prospectiq.enrichment.smtp_verify import VerificationResult, verify_email

__all__ = [
    "LeadEnricher",
    "VerificationResult",
    "apply_pattern",
    "calculate_lead_score",
    "detect_pattern",
    "enrich_lead",
    "extract_domain",
    "generate_candidates",
    "infer_from_observed",
    "score_email_candidate",
    "split_name",
    "verify_email",
]
