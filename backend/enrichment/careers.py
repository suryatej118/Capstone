import requests
from backend.enrichment.domain import extract_urls


CAREERS_PATHS = [
    "/careers",
    "/career",
    "/jobs",
    "/job",
    "/work-with-us",
    "/work-with-us/",
    "/join-us",
    "/join-us/",
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

    return any(
        keyword in text_lower
        for keyword in CAREERS_KEYWORDS
    )



def detect_careers_page(
    text: str,
    domain: str | None = None,
) -> dict:
    """
    Determine whether a job post contains evidence of a careers page.

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

    # First check URLs directly present in the job post.
    urls = extract_urls(text)

    for url in urls:
        url_lower = url.lower()

        if any(
            path in url_lower
            for path in CAREERS_PATHS
        ):
            return {
                "present": True,
                "url": url,
                "method": "url",
            }

    # Check the job-post text itself for hiring/careers language.
    if _contains_careers_keyword(text):
        return {
            "present": True,
            "url": None,
            "method": "keyword",
        }

    # If we know the company domain, check common careers paths.
    if domain:
        base_url = f"https://{domain}"

        for path in CAREERS_PATHS:
            url = f"{base_url}{path}"

            try:
                response = requests.get(
                    url,
                    timeout=5,
                    allow_redirects=True,
                )

                if response.status_code == 200:
                    if _contains_careers_keyword(response.text):
                        return {
                            "present": True,
                            "url": response.url,
                            "method": "website",
                        }

            except requests.RequestException:
                continue

    return {
        "present": False,
        "url": None,
        "method": "none",
    }