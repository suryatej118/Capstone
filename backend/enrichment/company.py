
import re
from typing import Optional


# Company name is captured before a recognizable recruitment phrase.
COMPANY_PATTERNS = [
    # "ABC Technologies is hiring..."
    # "ABC Technologies is inviting applications..."
    re.compile(
        r"\b([A-Z][A-Za-z0-9&.,' -]{2,80}?)"
        r"\s+(?:is|are)\s+"
        r"(?:hiring|recruiting|looking for|"
        r"inviting applications|announcing vacancies|"
        r"expanding its team)\b"
    ),

    # "Join Microsoft as a Software Engineer"
    # "Work at Google for backend development"
    re.compile(
        r"\b(?:Join|Work at|Work with)\s+"
        r"([A-Z][A-Za-z0-9&.,' -]{1,80}?)"
        r"(?=\s+(?:as|for|to)\b|[.!?,]|$)",
        re.IGNORECASE,
    ),

    # "We are hiring at Google for backend engineers"
    re.compile(
        r"\bhiring\s+at\s+"
        r"([A-Z][A-Za-z0-9&.,' -]{2,80}?)"
        r"(?=\s+(?:as|for|to)\b|[.!?,]|$)"
    ),

    # "Global Tech Solutions Pvt. Ltd. announces recruitment..."
    # "ABC Technologies announces hiring..."
    re.compile(
        r"\b([A-Z][A-Za-z0-9&.,' -]{2,80}?)"
        r"\s+(?:announces|announced|starts|launches|"
        r"begins)\s+"
        r"(?:its\s+)?(?:recruitment|hiring|"
        r"recruiting|campus recruitment|"
        r"job openings|vacancies)\b"
    ),
]


def extract_company_name(text: str) -> Optional[str]:
    """
    Extract a likely company name from job-posting text.

    This is a heuristic extractor. It does not establish
    the legal identity of a company.
    """

    if not text or not text.strip():
        return None

    for pattern in COMPANY_PATTERNS:
        match = pattern.search(text)

        if match:
            company_name = match.group(1).strip()
            company_name = company_name.rstrip(".,;:")

            if company_name:
                return company_name

    return None
