import os
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv


load_dotenv()

GITHUB_API_URL = "https://api.github.com"
REQUEST_TIMEOUT = 5
RECENT_ACTIVITY_DAYS = 180


def extract_github_org(text: str) -> str | None:
    """
    Extract a GitHub organization name from a job post.

    Only accepts URLs on github.com.
    """

    if not text:
        return None

    words = text.split()

    for word in words:
        candidate = word.strip("()[]{}<>,.;:\"'")

        if not candidate.startswith(
            ("https://github.com/", "http://github.com/")
        ):
            continue

        parsed = urlparse(candidate)

        if parsed.netloc.lower() != "github.com":
            continue

        parts = [
            part
            for part in parsed.path.split("/")
            if part
        ]

        if not parts:
            continue

        org_name = parts[0]

        # Ignore GitHub's special pages.
        if org_name.lower() in {
            "features",
            "topics",
            "marketplace",
            "explore",
            "settings",
            "login",
            "signup",
        }:
            continue

        return org_name

    return None


def _get_headers() -> dict:
    """
    Return GitHub API headers.

    A token is optional. Public API access works without one,
    but an authenticated token provides a higher rate limit.
    """

    token = os.getenv("GITHUB_TOKEN")

    headers = {
        "Accept": "application/vnd.github+json",
    }

    if token:
        headers["Authorization"] = f"Bearer {token}"

    return headers


def _get_organization(org_name: str) -> dict | None:
    """
    Retrieve a GitHub organization if the API request succeeds.

    Returns None if the organization cannot be retrieved.
    """

    if not org_name:
        return None

    url = f"{GITHUB_API_URL}/orgs/{org_name}"

    try:
        response = requests.get(
            url,
            headers=_get_headers(),
            timeout=REQUEST_TIMEOUT,
        )

        if response.status_code != 200:
            return None

        organization = response.json()

    except (requests.RequestException, ValueError):
        return None

    if not isinstance(organization, dict):
        return None

    return organization


def _get_recent_public_activity(
    org_name: str,
) -> bool | None:
    """
    Check for public organization activity within the last 180 days.

    Returns:
        True: Recent public activity was found.
        False: A valid API response contained no recent activity.
        None: The activity check could not be completed reliably.
    """

    url = (
        f"{GITHUB_API_URL}/orgs/"
        f"{org_name}/events/public"
    )

    try:
        response = requests.get(
            url,
            headers=_get_headers(),
            params={"per_page": 100},
            timeout=REQUEST_TIMEOUT,
        )

    except requests.RequestException:
        return None

    if response.status_code != 200:
        return None

    try:
        events = response.json()
    except ValueError:
        return None

    if not isinstance(events, list):
        return None

    cutoff = datetime.now(timezone.utc) - timedelta(
        days=RECENT_ACTIVITY_DAYS
    )

    for event in events:
        if not isinstance(event, dict):
            continue

        created_at = event.get("created_at")

        if not isinstance(created_at, str) or not created_at:
            continue

        try:
            event_time = datetime.fromisoformat(
                created_at.replace("Z", "+00:00")
            )

            # Treat timestamps without timezone information as UTC.
            if event_time.tzinfo is None:
                event_time = event_time.replace(
                    tzinfo=timezone.utc
                )
            else:
                event_time = event_time.astimezone(
                    timezone.utc
                )

        except (ValueError, TypeError):
            continue

        if event_time >= cutoff:
            return True

    return False


def _website_matches_domain(
    website: str | None,
    company_domain: str | None,
) -> bool:
    """
    Check whether the GitHub organization's website
    corresponds to the company's domain.
    """

    if not website or not company_domain:
        return False

    website = website.lower()
    company_domain = company_domain.lower()

    return company_domain in website


def get_github_activity(
    org_name: str | None,
    company_domain: str | None = None,
) -> dict | None:
    """
    Collect raw GitHub organization activity signals.

    Scoring is handled by hiring_intent.py.

    A failed activity check is represented by None rather
    than False, so API failures aren't treated as inactivity.
    """

    if not org_name:
        return None

    organization = _get_organization(org_name)

    if organization is None:
        return {
            "exists": False,
            "recent_activity": None,
            "website": None,
        }

    recent_activity = _get_recent_public_activity(
        org_name
    )

    return {
        "exists": True,
        "recent_activity": recent_activity,
        "website": organization.get("blog"),
    }
