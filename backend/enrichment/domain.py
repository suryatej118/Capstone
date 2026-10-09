"""
Domain and email extraction utilities.

This module performs local text processing only.
It does not make network requests.
"""

import re
from typing import List, Optional

import tldextract


EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)

URL_PATTERN = re.compile(
    r"https?://[^\s<>\"]+",
    re.IGNORECASE,
)


def extract_emails(text: str) -> List[str]:
    """Extract email addresses from text."""
    if not text:
        return []

    return list(dict.fromkeys(
        match.group(0).lower()
        for match in EMAIL_PATTERN.finditer(text)
    ))


def extract_urls(text: str) -> List[str]:
    """Extract HTTP/HTTPS URLs from text."""
    if not text:
        return []

    return list(dict.fromkeys(
        match.group(0).rstrip(".,;:!?)]}")
        for match in URL_PATTERN.finditer(text)
    ))


def normalize_domain(value: Optional[str]) -> Optional[str]:
    """
    Convert an email, URL, or domain into its registrable domain.

    Examples:
        hr@www.acme.com -> acme.com
        https://www.acme.com/careers -> acme.com
        jobs.acme.com -> acme.com
    """
    if not value:
        return None

    value = value.strip().lower()

    # If an email was supplied, extract its domain first.
    if "@" in value:
        value = value.split("@", 1)[1]

    # Remove URL scheme.
    value = re.sub(r"^https?://", "", value)

    # Remove www.
    value = re.sub(r"^www\.", "", value)

    # Remove path/query/fragment.
    value = value.split("/", 1)[0]
    value = value.split("?", 1)[0]
    value = value.split("#", 1)[0]

    extracted = tldextract.extract(value)

    if not extracted.domain or not extracted.suffix:
        return None

    return f"{extracted.domain}.{extracted.suffix}"


def extract_domains(text: str) -> List[str]:
    """
    Extract normalized registrable domains from URLs and email addresses.
    """
    if not text:
        return []

    domains = []

    for email in extract_emails(text):
        domain = normalize_domain(email)

        if domain:
            domains.append(domain)

    for url in extract_urls(text):
        domain = normalize_domain(url)

        if domain:
            domains.append(domain)

    return list(dict.fromkeys(domains))