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
    Retrieve a GitHub organization if it exists.
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

    except requests.RequestException:
        return None

    if response.status_code != 200:
        return None

    return response.json()


def _get_recent_public_activity(org_name: str) -> bool:
    """
    Determine whether the organization has public activity
    within the last 180 days.
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
        return False

    if response.status_code != 200:
        return False

    events = response.json()

    if not isinstance(events, list):
        return False

    cutoff = datetime.now(timezone.utc) - timedelta(
        days=RECENT_ACTIVITY_DAYS
    )

    for event in events:
        created_at = event.get("created_at")

        if not created_at:
            continue

        try:
            event_time = datetime.fromisoformat(
                created_at.replace("Z", "+00:00")
            )

        except ValueError:
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
    """

    if not org_name:
        return None

    organization = _get_organization(org_name)

    if organization is None:
        return {
            "exists": False,
            "recent_activity": False,
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