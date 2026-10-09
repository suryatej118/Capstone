import re
from typing import Optional


COMPANY_PATTERNS = [
    # "Acme Technologies is hiring..."
    re.compile(
        r"\b([A-Z][A-Za-z0-9&.,' -]{2,80}?)"
        r"\s+(?:is|are)\s+(?:hiring|recruiting|looking for)\b"
    ),

    # "Join Microsoft as a Software Engineer"
    re.compile(
        r"\b(?:[Jj]oin|[Ww]ork at|[Ww]ork with)\s+"
        r"([A-Z][A-Za-z0-9&.,'-]*?)"
        r"(?=\s+(?:as|for|to)\b|[.!?,]|$)"
    ),

    # "We are hiring at Google for backend engineers"
    re.compile(
        r"\bhiring\s+at\s+"
        r"([A-Z][A-Za-z0-9&.,' -]{2,80}?)"
        r"(?=\s+(?:as|for|to)\b|[.!?,]|$)"
    ),
]


def extract_company_name(text: str) -> Optional[str]:
    """
    Extract a likely company name from job-posting text.

    This is a lightweight heuristic extractor. It does not guarantee
    that the extracted text is the legally registered company name.
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