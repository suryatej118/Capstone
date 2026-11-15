import requests
from unittest.mock import patch

from backend.enrichment.domain_verification import (
    check_dns,
    check_website,
    verify_company_domain,
)


def test_invalid_domain_returns_unknown():
    result = verify_company_domain("invalid")

    assert result["status"] == "unknown"
    assert result["ownership_verified"] is False


def test_matching_official_domain():
    with (
        patch(
            "backend.enrichment.domain_verification.check_dns",
            return_value={"status": "available", "resolves": True},
        ),
        patch(
            "backend.enrichment.domain_verification.check_website",
            return_value={
                "status": "available",
                "url": "https://acme.com",
                "final_domain": "acme.com",
            },
        ),
    ):
        result = verify_company_domain(
            "https://www.acme.com/careers",
            "acme.com",
        )

    assert result["status"] == "verified"
    assert result["ownership_verified"] is True


def test_unrelated_domain_is_not_verified():
    with (
        patch(
            "backend.enrichment.domain_verification.check_dns",
            return_value={"status": "available", "resolves": True},
        ),
        patch(
            "backend.enrichment.domain_verification.check_website",
            return_value={
                "status": "available",
                "url": "https://example.com",
                "final_domain": "example.com",
            },
        ),
    ):
        result = verify_company_domain(
            "example.com",
            "acme.com",
        )

    assert result["status"] == "unknown"
    assert result["ownership_verified"] is False


def test_dns_failure():
    with patch(
        "backend.enrichment.domain_verification.socket.getaddrinfo",
        side_effect=OSError,
    ):
        result = check_dns("acme.com")

    assert result["status"] == "unknown"


def test_website_unavailable():
    with patch(
        "backend.enrichment.domain_verification.requests.get",
        side_effect=requests.exceptions.ConnectionError,
    ):
        result = check_website("acme.com")

    assert result["status"] == "unavailable"
