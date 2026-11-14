import re
from urllib.parse import urlparse

import requests


REQUEST_TIMEOUT = 5


def _extract_ats_from_url(url: str) -> tuple[str | None, str | None]:
    """
    Identify a supported ATS and its board/site identifier
    from a careers URL.
    """

    try:
        parsed = urlparse(url)
    except ValueError:
        return None, None

    host = parsed.netloc.lower()
    path = parsed.path.strip("/")

    # Greenhouse:
    # https://boards.greenhouse.io/company
    if "greenhouse.io" in host:
        parts = [part for part in path.split("/") if part]

        if parts:
            return "greenhouse", parts[-1]

    # Lever:
    # https://jobs.lever.co/company
    if "lever.co" in host:
        parts = [part for part in path.split("/") if part]

        if parts:
            return "lever", parts[-1]

    # Ashby:
    # https://jobs.ashbyhq.com/company
    if "ashbyhq.com" in host:
        parts = [part for part in path.split("/") if part]

        if parts:
            return "ashby", parts[-1]

    return None, None


def _count_greenhouse_jobs(board_token: str) -> int:
    url = (
        "https://boards-api.greenhouse.io/v1/boards/"
        f"{board_token}/jobs"
    )

    response = requests.get(
        url,
        params={"content": "false"},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()

    data = response.json()

    return int(data.get("meta", {}).get("total", 0))


def _count_lever_jobs(site: str) -> int:
    """
    Count all published Lever job postings using pagination.
    """

    url = f"https://api.lever.co/v0/postings/{site}"

    total = 0
    skip = 0
    page_size = 100

    while True:
        response = requests.get(
            url,
            params={
                "mode": "json",
                "limit": page_size,
                "skip": skip,
            },
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

        data = response.json()

        if not isinstance(data, list):
            break

        total += len(data)

        if len(data) < page_size:
            break

        skip += page_size

    return total


def _count_ashby_jobs(job_board_name: str) -> int:
    url = (
        "https://api.ashbyhq.com/posting-api/job-board/"
        f"{job_board_name}"
    )

    response = requests.get(
        url,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()

    data = response.json()

    jobs = data.get("jobs", [])

    if not isinstance(jobs, list):
        return 0

    return len(jobs)


def get_active_job_postings(
    careers_url: str | None,
) -> dict:
    """
    Determine the number of publicly published job postings
    when the company's careers URL belongs to a supported ATS.

    Returns:
        {
            "count": int | None,
            "ats": str | None,
            "source": str | None,
        }
    """

    if not careers_url:
        return {
            "count": None,
            "ats": None,
            "source": None,
        }

    ats, identifier = _extract_ats_from_url(careers_url)

    if not ats or not identifier:
        return {
            "count": None,
            "ats": None,
            "source": None,
        }

    try:
        if ats == "greenhouse":
            count = _count_greenhouse_jobs(identifier)

        elif ats == "lever":
            count = _count_lever_jobs(identifier)

        elif ats == "ashby":
            count = _count_ashby_jobs(identifier)

        else:
            return {
                "count": None,
                "ats": None,
                "source": None,
            }

    except requests.RequestException:
        return {
            "count": None,
            "ats": ats,
            "source": None,
        }

    return {
        "count": count,
        "ats": ats,
        "source": careers_url,
    }