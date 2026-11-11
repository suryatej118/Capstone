from backend.enrichment.domain import (
    extract_emails,
    extract_url_domains,
)


def test_email_domain_is_not_company_website_domain():
    text = (
        "Global Tech Solutions is hiring. "
        "Contact globaltech.hr2026@gmail.com"
    )

    assert extract_emails(text) == [
        "globaltech.hr2026@gmail.com"
    ]

    assert extract_url_domains(text) == []


def test_company_website_domain_is_extracted():
    text = "Apply at https://www.example.com/careers"

    assert extract_url_domains(text) == ["example.com"]


def test_email_and_website_are_separated():
    text = (
        "Contact hr@example.com. "
        "Visit https://www.example.com/careers"
    )

    assert extract_emails(text) == ["hr@example.com"]
    assert extract_url_domains(text) == ["example.com"]