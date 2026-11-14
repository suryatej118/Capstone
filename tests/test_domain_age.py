from datetime import datetime
from unittest.mock import Mock, patch

from backend.enrichment.domain_age import get_domain_age_years


def test_domain_age_from_single_creation_date():
    mock_result = Mock()
    mock_result.creation_date = datetime(2010, 1, 1)

    with patch(
        "backend.enrichment.domain_age.whois.whois",
        return_value=mock_result,
    ):
        age = get_domain_age_years("example.com")

    assert age is not None
    assert age > 15


def test_domain_age_from_creation_date_list():
    mock_result = Mock()
    mock_result.creation_date = [
        datetime(2015, 1, 1),
        datetime(2010, 1, 1),
    ]

    with patch(
        "backend.enrichment.domain_age.whois.whois",
        return_value=mock_result,
    ):
        age = get_domain_age_years("example.com")

    assert age is not None
    assert age > 15


def test_domain_age_returns_none_when_creation_date_missing():
    mock_result = Mock()
    mock_result.creation_date = None

    with patch(
        "backend.enrichment.domain_age.whois.whois",
        return_value=mock_result,
    ):
        age = get_domain_age_years("example.com")

    assert age is None


def test_domain_age_returns_none_when_whois_fails():
    with patch(
        "backend.enrichment.domain_age.whois.whois",
        side_effect=Exception("WHOIS unavailable"),
    ):
        age = get_domain_age_years("example.com")

    assert age is None


def test_domain_age_handles_empty_domain():
    assert get_domain_age_years("") is None