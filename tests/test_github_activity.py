from unittest.mock import Mock, patch

from backend.enrichment.github_activity import (
    _website_matches_domain,
    extract_github_org,
    get_github_activity,
)


def test_extract_github_org():
    text = (
        "Check our engineering work at "
        "https://github.com/microsoft"
    )

    assert extract_github_org(text) == "microsoft"


def test_extract_github_org_with_trailing_punctuation():
    text = "GitHub: https://github.com/example."

    assert extract_github_org(text) == "example"


def test_extract_github_org_returns_none_when_missing():
    text = "Visit our company website for more information."

    assert extract_github_org(text) is None


def test_extract_github_org_ignores_special_pages():
    text = "Visit https://github.com/explore"

    assert extract_github_org(text) is None


def test_website_matches_company_domain():
    assert _website_matches_domain(
        "https://www.microsoft.com",
        "microsoft.com",
    ) is True


def test_website_does_not_match_company_domain():
    assert _website_matches_domain(
        "https://example.com",
        "microsoft.com",
    ) is False


def test_missing_org_returns_unknown():
    result = get_github_activity(None, "microsoft.com")

    assert result is None


def test_github_organization_exists_without_recent_activity():
    organization = {
        "login": "example",
        "blog": "https://example.com",
    }

    activity_response = []

    mock_org_response = Mock()
    mock_org_response.status_code = 200
    mock_org_response.json.return_value = organization

    mock_activity_response = Mock()
    mock_activity_response.status_code = 200
    mock_activity_response.json.return_value = activity_response

    with patch(
        "backend.enrichment.github_activity.requests.get",
        side_effect=[
            mock_org_response,
            mock_activity_response,
        ],
    ):
        result = get_github_activity(
            "example",
            "example.com",
        )

    assert result["exists"] is True
    assert result["recent_activity"] is False
    assert result["website"] == "https://example.com"


def test_github_organization_with_recent_activity():
    organization = {
        "login": "example",
        "blog": "https://example.com",
    }

    activity_response = [
        {
            "type": "PushEvent",
            "created_at": "2099-01-01T00:00:00Z",
        }
    ]

    mock_org_response = Mock()
    mock_org_response.status_code = 200
    mock_org_response.json.return_value = organization

    mock_activity_response = Mock()
    mock_activity_response.status_code = 200
    mock_activity_response.json.return_value = activity_response

    with patch(
        "backend.enrichment.github_activity.requests.get",
        side_effect=[
            mock_org_response,
            mock_activity_response,
        ],
    ):
        result = get_github_activity(
            "example",
            "example.com",
        )

    assert result["exists"] is True
    assert result["recent_activity"] is True
    assert result["website"] == "https://example.com"