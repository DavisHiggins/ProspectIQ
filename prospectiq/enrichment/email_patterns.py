"""Corporate email pattern detection and candidate generation.

Organizations issue addresses from a house style — ``first.last@``, ``flast@``,
and so on. Observing one address on a domain reveals that style, which lets a
colleague's address be inferred. Inferred addresses are always labelled
``pattern`` and scored well below observed ones, because they are educated
guesses rather than facts.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

#: Known local-part styles, mapped to how they are rendered.
PATTERN_TEMPLATES: dict[str, str] = {
    "first.last": "{first}.{last}",
    "firstlast": "{first}{last}",
    "first": "{first}",
    "f.last": "{f}.{last}",
    "flast": "{f}{last}",
    "first_last": "{first}_{last}",
}

#: Generic mailboxes worth trying when no personal address can be inferred.
ROLE_ADDRESSES: tuple[str, ...] = ("contact", "info", "hello")

_NON_ALPHA = re.compile(r"[^a-z]")


def extract_domain(url: str) -> str:
    """Reduce a URL or bare host to a normalized domain.

    Returns an empty string when nothing domain-shaped can be extracted.
    """
    if not url:
        return ""

    candidate = url.strip()
    if not candidate.startswith(("http://", "https://")):
        candidate = f"https://{candidate}"

    try:
        host = urlparse(candidate).netloc
    except ValueError:
        return ""

    host = host.split("@")[-1].split(":")[0].lower()
    return host.removeprefix("www.")


def split_name(full_name: str) -> tuple[str, str]:
    """Split a display name into normalized ``(first, last)`` parts.

    Returns ``("", "")`` when the name has no usable first/last structure, such
    as a mononym or a handle full of punctuation.
    """
    if not full_name:
        return "", ""

    parts = [_NON_ALPHA.sub("", part.lower()) for part in full_name.strip().split()]
    parts = [part for part in parts if part]

    if len(parts) < 2:
        return "", ""
    return parts[0], parts[-1]


def detect_pattern(local_part: str, first: str = "", last: str = "") -> str:
    """Infer the house style from an observed local part.

    When ``first`` and ``last`` are supplied, the observed address is matched
    against each template so the detection is evidence-based rather than
    guessed from shape alone.

    Args:
        local_part: The portion of an observed address before the ``@``.
        first: Known first name of the person that address belongs to.
        last: Known last name of that person.

    Returns:
        A key from :data:`PATTERN_TEMPLATES`, or an empty string.
    """
    local = local_part.strip().lower()
    if not local:
        return ""

    if first and last:
        for name, template in PATTERN_TEMPLATES.items():
            if local == template.format(first=first, last=last, f=first[0]):
                return name
        return ""

    # No reference name available — fall back to structural inference.
    if "." in local:
        head, _, tail = local.partition(".")
        if head and tail:
            return "f.last" if len(head) == 1 else "first.last"
    if "_" in local:
        return "first_last"
    if local.isalpha():
        return "first"
    return ""


def apply_pattern(pattern: str, first: str, last: str, domain: str) -> str:
    """Render an address for ``first``/``last`` in the given house style.

    Returns an empty string for unknown patterns or incomplete names.
    """
    template = PATTERN_TEMPLATES.get(pattern)
    if not template or not first or not last or not domain:
        return ""
    return f"{template.format(first=first, last=last, f=first[0])}@{domain}"


def infer_from_observed(full_name: str, domain: str, observed_emails: list[str]) -> str:
    """Infer a person's address from other addresses on the same domain.

    Args:
        full_name: The lead's display name.
        domain: The company domain.
        observed_emails: Addresses actually seen on that domain.

    Returns:
        The inferred address, or an empty string when the pattern could not be
        established or the result would duplicate an observed address.
    """
    first, last = split_name(full_name)
    if not (first and last and domain):
        return ""

    suffix = f"@{domain.lower()}"
    on_domain = [e for e in observed_emails if e.lower().endswith(suffix)]
    if not on_domain:
        return ""

    for observed in on_domain:
        local = observed.split("@")[0].lower()
        pattern = detect_pattern(local) or ""
        if not pattern:
            continue
        candidate = apply_pattern(pattern, first, last, domain)
        if candidate and candidate.lower() not in {e.lower() for e in on_domain}:
            return candidate

    return ""


def generate_candidates(full_name: str, domain: str) -> list[str]:
    """Generate plausible addresses for a person at a domain, best guess first.

    Returns an empty list when the name lacks first/last structure. Role
    addresses are appended last, since they reach an inbox but not a person.
    """
    first, last = split_name(full_name)
    if not domain:
        return []

    candidates: list[str] = []
    if first and last:
        candidates = [
            apply_pattern(pattern, first, last, domain)
            for pattern in ("first.last", "first", "firstlast", "flast", "f.last")
        ]
    elif first:
        candidates = [f"{first}@{domain}"]

    candidates.extend(f"{role}@{domain}" for role in ROLE_ADDRESSES)

    seen: set[str] = set()
    unique: list[str] = []
    for candidate in candidates:
        if candidate and candidate not in seen:
            seen.add(candidate)
            unique.append(candidate)
    return unique
