
import logging
from urllib.parse import urlparse

import requests

from backend.enrichment.domain import extract_urls


logger = logging.getLogger(__name__)

CAREERS_PATHS = [
    "/careers",
    "/career",
    "/jobs",
    "/job",
    "/work-with-us",
    "/join-us",
]

CAREERS_KEYWORDS = [
    "careers",
    "career opportunities",
    "job opportunities",
    "we are hiring",
    "we're hiring",
    "join our team",
    "open positions",
    "job openings",
]


def _contains_careers_keyword(text: str) -> bool:
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in CAREERS_KEYWORDS)


def _has_careers_path(url: str) -> bool:
    """Check the URL path, rather than matching arbitrary URL substrings."""
    try:
        path = urlparse(url).path.rstrip("/").lower()
        return any(
            path == careers_path.rstrip("/")
            for careers_path in CAREERS_PATHS
        )
    except (TypeError, ValueError):
        return False


def detect_careers_page(
    text: str,
    domain: str | None = None,
) -> dict:
    """
    Detect evidence of a careers page.

    `present=True` means a careers URL was found or a page was verified.
    Hiring-related wording alone is not proof that a careers page exists.

    Returns:
        {
            "present": bool,
            "url": str | None,
            "method": str
        }
    """
    if not text or not text.strip():
        return {
            "present": False,
            "url": None,
            "method": "none",
        }

    # 1. Look for a careers URL directly in the supplied message.
    for url in extract_urls(text):
        if _has_careers_path(url):
            return {
                "present": True,
                "url": url,
                "method": "url",
            }

    # 2. If a company domain is available, check common careers paths.
    if domain:
        clean_domain = domain.strip()

        # Avoid constructing a URL from malformed or unexpected input.
        if (
            clean_domain
            and "://" not in clean_domain
            and "/" not in clean_domain
            and " " not in clean_domain
        ):
            base_url = f"https://{clean_domain}"

            for path in CAREERS_PATHS:
                url = f"{base_url}{path}"

                try:
                    response = requests.get(
                        url,
                        timeout=5,
                        allow_redirects=True,
                    )

                    if response.status_code != 200:
                        continue

                    # Require both a careers-like final URL and hiring-related
                    # content before counting the page as verified.
                    if (
                        _has_careers_path(response.url)
                        and _contains_careers_keyword(response.text)
                    ):
                        return {
                            "present": True,
                            "url": response.url,
                            "method": "website",
                        }

                except requests.RequestException:
                    logger.debug(
                        "Careers-page request failed for %s",
                        url,
                        exc_info=True,
                    )

    # 3. Keyword wording is useful context, but not proof of a careers page.
    if _contains_careers_keyword(text):
        return {
            "present": False,
            "url": None,
            "method": "keyword_mention",
        }

    return {
        "present": False,
        "url": None,
        "method": "none",
    }
