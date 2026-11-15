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
    Search OpenCorporates and return ranked company-name candidates.

    A registry match is supporting company-registration evidence.
    It does not verify recruiter identity or job legitimacy.
    """

    if not company_name or not company_name.strip():
        return {
            "matched": False,
            "match_type": "invalid_input",
            "similarity": 0.0,
            "company": None,
            "candidates": [],
        }

    results = search_company(company_name)

    companies = (
        results
        .get("results", {})
        .get("companies", [])
    )

    normalized_input = _normalize_company_name(company_name)

    candidates = []

    for item in companies:
        company = item.get("company", {})
        returned_name = company.get("name")

        if not returned_name:
            continue

        normalized_returned = _normalize_company_name(
            returned_name
        )

        if not normalized_input or not normalized_returned:
            continue

        similarity = SequenceMatcher(
            None,
            normalized_input,
            normalized_returned,
        ).ratio()

        candidates.append({
            "name": returned_name,
            "company_number": company.get("company_number"),
            "jurisdiction_code": company.get("jurisdiction_code"),
            "current_status": company.get("current_status"),
            "opencorporates_url": company.get("opencorporates_url"),
            "similarity": round(similarity, 3),
            "exact_name_match": (
                normalized_input == normalized_returned
            ),
        })

    candidates.sort(
        key=lambda candidate: candidate["similarity"],
        reverse=True,
    )

    best_match = candidates[0] if candidates else None

    if best_match is None:
        return {
            "matched": False,
            "match_type": "no_match",
            "similarity": 0.0,
            "company": None,
            "candidates": [],
        }

    matched = best_match["similarity"] >= min_similarity

    match_type = (
        "exact"
        if best_match["exact_name_match"]
        else "fuzzy" if matched
        else "below_threshold"
    )

    return {
        "matched": matched,
        "match_type": match_type,
        "similarity": best_match["similarity"],
        "company": best_match,
        "candidates": candidates,
    }
