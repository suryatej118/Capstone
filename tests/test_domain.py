from backend.enrichment.domain import (
    extract_emails,
    extract_urls,
    extract_domains,
    normalize_domain,
)


def test_extract_emails():
    text = "Contact hr@acme.com or careers@acme.com"
    assert extract_emails(text) == [
        "hr@acme.com",
        "careers@acme.com",
    ]


def test_extract_urls():
    text = (
        "Visit https://www.acme.com/careers "
        "or https://jobs.acme.com/apply."
    )

    assert extract_urls(text) == [
        "https://www.acme.com/careers",
        "https://jobs.acme.com/apply",
    ]


def test_normalize_domain_from_url():
    assert normalize_domain(
        "https://www.acme.com/careers"
    ) == "acme.com"


def test_normalize_domain_from_email():
    assert normalize_domain(
        "hr@jobs.acme.com"
    ) == "acme.com"


def test_normalize_domain_from_subdomain():
    assert normalize_domain(
        "jobs.acme.com"
    ) == "acme.com"


def test_extract_domains_deduplicates_subdomains():
    text = (
        "hr@acme.com "
        "https://www.acme.com/careers "
        "https://jobs.acme.com/apply"
    )

    assert extract_domains(text) == ["acme.com"]