
"""
Company domain verification utilities.

A domain mentioned in a job posting is only a candidate.
DNS and website availability are supporting evidence,
not proof of company ownership.
"""

import socket
from typing import Any, Optional
from urllib.parse import urlparse

import requests

from backend.enrichment.domain import normalize_domain


def check_dns(domain: str) -> dict:
    """Check whether a domain resolves through DNS."""
    normalized = normalize_domain(domain)

    if not normalized:
        return {
            "status": "unknown",
            "resolves": None,
        }

    try:
        socket.getaddrinfo(normalized, None)

        return {
            "status": "available",
            "resolves": True,
        }

    except socket.gaierror:
        return {
            "status": "unavailable",
            "resolves": False,
        }

    except OSError:
        return {
            "status": "unknown",
            "resolves": None,
        }


def check_website(domain: str) -> dict:
    """Check whether the candidate domain has a reachable website."""
    normalized = normalize_domain(domain)

    if not normalized:
        return {
            "status": "unknown",
            "url": None,
            "final_domain": None,
        }

    for scheme in ("https", "http"):
        url = f"{scheme}://{normalized}"

        try:
            response = requests.get(
                url,
                timeout=5,
                allow_redirects=True,
                headers={
                    "User-Agent": "JobScamRadar/1.0"
                },
            )

            final_domain = normalize_domain(response.url)

            if response.status_code < 400:
                return {
                    "status": "available",
                    "url": response.url,
                    "final_domain": final_domain,
                    "status_code": response.status_code,
                }

        except requests.RequestException:
            continue

    return {
        "status": "unavailable",
        "url": None,
        "final_domain": None,
    }


def verify_company_domain(
    candidate_domain: str,
    official_domain: Optional[str] = None,
) -> dict[str, Any]:
    """
    Evaluate a candidate domain against independently supplied
    official-domain evidence.

    DNS and website availability alone never establish ownership.
    """

    normalized_candidate = normalize_domain(candidate_domain)
    normalized_official = normalize_domain(official_domain)

    if not normalized_candidate:
        return {
            "status": "unknown",
            "candidate_domain": None,
            "official_domain": normalized_official,
            "ownership_verified": False,
            "reason": "invalid_candidate_domain",
        }

    dns_result = check_dns(normalized_candidate)
    website_result = check_website(normalized_candidate)

    ownership_verified = bool(
        normalized_official
        and normalized_candidate == normalized_official
    )

    if ownership_verified:
        status = "verified"
        reason = "matches_independently_supplied_official_domain"
    elif (
        dns_result["status"] == "unavailable"
        and website_result["status"] == "unavailable"
    ):
        status = "unverified"
        reason = "domain_and_website_unavailable"
    else:
        status = "unknown"
        reason = "domain_ownership_not_independently_established"

    return {
        "status": status,
        "candidate_domain": normalized_candidate,
        "official_domain": normalized_official,
        "ownership_verified": ownership_verified,
        "dns": dns_result,
        "website": website_result,
        "reason": reason,
    }
