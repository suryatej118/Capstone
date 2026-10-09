import json
import os
import re
import threading
import time
from difflib import SequenceMatcher


from backend.enrichment.cache import (
    get_cached_result,
    save_cached_result,
)

import requests
from dotenv import load_dotenv

load_dotenv()


BASE_URL = "https://api.opencorporates.com/v0.4"
API_TOKEN = os.getenv("OPENCORPORATES_API_KEY")

# OpenCorporates public-benefit key:
# maximum 2 requests per second.
MIN_REQUEST_INTERVAL = 0.5

_rate_lock = threading.Lock()
_last_request_time = 0.0


def _wait_for_rate_limit() -> None:
    """
    Ensure that OpenCorporates requests are spaced at least
    0.5 seconds apart.
    """
    global _last_request_time

    with _rate_lock:
        now = time.monotonic()
        elapsed = now - _last_request_time

        if elapsed < MIN_REQUEST_INTERVAL:
            time.sleep(MIN_REQUEST_INTERVAL - elapsed)

        _last_request_time = time.monotonic()


def search_company(company_name: str) -> dict:
    """
    Search OpenCorporates for companies matching a company name.

    Results are cached locally to avoid repeated API calls for the
    same company name.
    """

    if not API_TOKEN:
        raise RuntimeError("OPENCORPORATES_API_KEY is not configured")

    if not company_name or not company_name.strip():
        raise ValueError("company_name cannot be empty")

    normalized_name = _normalize_company_name(company_name)

    cached_result = get_cached_result(normalized_name)

    if cached_result is not None:
        return json.loads(cached_result)

    _wait_for_rate_limit()

    url = f"{BASE_URL}/companies/search"

    headers = {
        "X-API-TOKEN": API_TOKEN
    }

    params = {
        "q": company_name.strip(),
        "order": "score",
        "per_page": 5,
    }

    response = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=10,
    )

    response.raise_for_status()

    result = response.json()

    save_cached_result(
        normalized_name,
        json.dumps(result),
    )

    return result

def _normalize_company_name(name: str) -> str:
    """
    Normalize a company name for comparison.

    Removes punctuation, converts to lowercase, and removes
    common legal entity suffixes.
    """

    name = name.lower().strip()

    # Replace punctuation with spaces.
    name = re.sub(r"[^a-z0-9\s]", " ", name)

    # Common legal entity suffixes.
    legal_suffixes = {
        "inc",
        "incorporated",
        "corp",
        "corporation",
        "co",
        "company",
        "ltd",
        "limited",
        "llc",
        "llp",
        "plc",
        "pvt",
        "private",
    }

    words = [
        word
        for word in name.split()
        if word not in legal_suffixes
    ]

    return " ".join(words)

def match_company_name(
    company_name: str,
    min_similarity: float = 0.85,
) -> dict:
    """
    Search OpenCorporates and determine whether a sufficiently
    similar company name was found.

    Returns a normalized result instead of exposing the raw API response.
    """

    results = search_company(company_name)

    companies = (
        results
        .get("results", {})
        .get("companies", [])
    )

    best_match = None
    best_similarity = 0.0

    normalized_input = _normalize_company_name(company_name)

    for item in companies:
        company = item.get("company", {})
        returned_name = company.get("name")

        if not returned_name:
            continue

        normalized_returned = _normalize_company_name(returned_name)

        similarity = SequenceMatcher(
            None,
            normalized_input,
            normalized_returned,
        ).ratio()

        if similarity > best_similarity:
            best_similarity = similarity
            best_match = company

    if best_match is None:
        return {
            "matched": False,
            "similarity": 0.0,
            "company": None,
        }

    return {
        "matched": best_similarity >= min_similarity,
        "similarity": round(best_similarity, 3),
        "company": {
            "name": best_match.get("name"),
            "company_number": best_match.get("company_number"),
            "jurisdiction_code": best_match.get("jurisdiction_code"),
            "current_status": best_match.get("current_status"),
            "opencorporates_url": best_match.get("opencorporates_url"),
        },
    }