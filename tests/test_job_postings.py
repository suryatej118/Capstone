from unittest.mock import Mock, patch
from backend.enrichment.job_postings import (
    _extract_ats_from_url,
    get_active_job_postings,
)


def test_extract_greenhouse_ats():
    ats, identifier = _extract_ats_from_url(
        "https://boards.greenhouse.io/acme"
    )

    assert ats == "greenhouse"
    assert identifier == "acme"


def test_extract_lever_ats():
    ats, identifier = _extract_ats_from_url(
        "https://jobs.lever.co/acme"
    )

    assert ats == "lever"
    assert identifier == "acme"


def test_extract_ashby_ats():
    ats, identifier = _extract_ats_from_url(
        "https://jobs.ashbyhq.com/acme"
    )

    assert ats == "ashby"
    assert identifier == "acme"


def test_unknown_careers_url_returns_none():
    result = get_active_job_postings(
        "https://acme.com/careers"
    )

    assert result["count"] is None
    assert result["ats"] is None


def test_empty_url_returns_none():
    result = get_active_job_postings(None)

    assert result["count"] is None
    assert result["ats"] is None

def test_lever_pagination_counts_all_jobs():
    first_page = [{"id": str(i)} for i in range(100)]
    second_page = [{"id": str(i)} for i in range(100, 135)]

    mock_response_1 = Mock()
    mock_response_1.json.return_value = first_page
    mock_response_1.raise_for_status.return_value = None

    mock_response_2 = Mock()
    mock_response_2.json.return_value = second_page
    mock_response_2.raise_for_status.return_value = None

    with patch(
        "backend.enrichment.job_postings.requests.get",
        side_effect=[
            mock_response_1,
            mock_response_2,
        ],
    ):
        from backend.enrichment.job_postings import _count_lever_jobs

        result = _count_lever_jobs("example")

    assert result == 135