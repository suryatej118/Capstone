
"""
Company website discovery and identity checks.

Search results are untrusted candidate evidence.
A search result alone never verifies domain ownership.
"""

import logging
from typing import Optional
from urllib.parse import urlparse

import requests
from ddgs import DDGS

from backend.enrichment.domain import normalize_domain

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "JobScamRadar/1.0"
}

TIMEOUT = 6


def discover_company_website(company_name: str) -> dict:
    """Find a candidate company website using web search."""

    if not company_name or not company_name.strip():
        return {
            "status": "unknown",
            "candidate_domain": None,
            "url": None,
        }

    try:
        results = DDGS().text(
            f"{company_name} official website",
            max_results=5,
        )

        for result in results:
            url = result.get("href") or result.get("url")

            if not url:
                continue

            parsed = urlparse(url)

            if parsed.scheme not in ("http", "https"):
                continue

            domain = normalize_domain(url)

            if domain:
                return {
                    "status": "candidate",
                    "candidate_domain": domain,
                    "url": url,
                }

    except Exception:
        logger.exception("Company website discovery failed")

    return {
        "status": "unknown",
        "candidate_domain": None,
        "url": None,
    }


def check_website_identity(
    company_name: str,
    candidate_domain: str,
) -> dict:
    """
    Check whether the candidate website contains the claimed company name.

    This is weak identity evidence, not proof of ownership.
    """

    domain = normalize_domain(candidate_domain)

    if not company_name or not domain:
        return {
            "status": "unknown",
            "name_found": False,
            "domain": domain,
        }

    try:
        response = requests.get(
            f"https://{domain}",
            headers=HEADERS,
            timeout=TIMEOUT,
            allow_redirects=True,
        )
        response.raise_for_status()

        final_domain = normalize_domain(response.url)
        page_text = response.text[:500_000].lower()

        normalized_name = " ".join(
            company_name.lower().split()
        )

        name_found = normalized_name in page_text

        same_domain = final_domain == domain

        if name_found and same_domain:
            status = "candidate_match"
        elif not same_domain:
            status = "domain_mismatch"
        else:
            status = "unknown"

        return {
            "status": status,
            "name_found": name_found,
            "domain": domain,
            "final_domain": final_domain,
        }

    except requests.RequestException:
        logger.exception("Company website identity check failed")

        return {
            "status": "unknown",
            "name_found": False,
            "domain": domain,
        }


def evaluate_company_website(company_name: str) -> dict:
    """Discover and evaluate a candidate company website."""

    discovery = discover_company_website(company_name)

    if discovery["status"] != "candidate":
        return {
            "status": "unknown",
            "verified": False,
            "candidate_domain": None,
            "reason": "website_not_discovered",
        }

    identity = check_website_identity(
        company_name,
        discovery["candidate_domain"],
    )

    return {
        "status": identity["status"],
        "verified": False,
        "candidate_domain": discovery["candidate_domain"],
        "website_url": discovery["url"],
        "identity_evidence": identity,
        "reason": "independent_ownership_verification_required",
    }
