
from unittest.mock import patch

from backend.enrichment.company_website import (
    discover_company_website,
    check_website_identity,
    evaluate_company_website,
)


def test_discovery_empty_company():
    result = discover_company_website("")

    assert result["status"] == "unknown"


def test_discovery_finds_candidate():
    with patch(
        "backend.enrichment.company_website.DDGS"
    ) as mock_ddgs:
        mock_ddgs.return_value.text.return_value = [
            {"href": "https://www.acme.com"}
        ]

        result = discover_company_website("Acme Technologies")

    assert result["status"] == "candidate"
    assert result["candidate_domain"] == "acme.com"


def test_website_identity_name_match():
    with patch(
        "backend.enrichment.company_website.requests.get"
    ) as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.url = "https://acme.com"
        mock_get.return_value.text = "Welcome to Acme Technologies"

        result = check_website_identity(
            "Acme Technologies",
            "acme.com",
        )

    assert result["status"] == "candidate_match"
    assert result["name_found"] is True


def test_redirect_domain_mismatch():
    with patch(
        "backend.enrichment.company_website.requests.get"
    ) as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.url = "https://different.com"
        mock_get.return_value.text = "Acme Technologies"

        result = check_website_identity(
            "Acme Technologies",
            "acme.com",
        )

    assert result["status"] == "domain_mismatch"


def test_candidate_never_automatically_verified():
    with (
        patch(
            "backend.enrichment.company_website.discover_company_website",
            return_value={
                "status": "candidate",
                "candidate_domain": "acme.com",
                "url": "https://acme.com",
            },
        ),
        patch(
            "backend.enrichment.company_website.check_website_identity",
            return_value={
                "status": "candidate_match",
                "name_found": True,
                "domain": "acme.com",
                "final_domain": "acme.com",
            },
        ),
    ):
        result = evaluate_company_website("Acme Technologies")

    assert result["verified"] is False
    assert result["status"] == "candidate_match"
