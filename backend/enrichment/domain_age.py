from datetime import datetime, timezone

import whois


def _get_creation_date(domain: str):
    """
    Retrieve the domain creation date from WHOIS.

    WHOIS libraries may return either a single datetime or a list
    of datetimes, depending on the registrar.
    """

    result = whois.whois(domain)

    creation_date = result.creation_date

    if isinstance(creation_date, list):
        creation_dates = [
            date
            for date in creation_date
            if isinstance(date, datetime)
        ]

        if not creation_dates:
            return None

        return min(creation_dates)

    if isinstance(creation_date, datetime):
        return creation_date

    return None


def get_domain_age_years(domain: str) -> float | None:
    """
    Return the approximate age of a domain in years.

    Returns None when WHOIS information is unavailable.
    """

    if not domain or not domain.strip():
        return None

    domain = domain.strip().lower()

    try:
        creation_date = _get_creation_date(domain)

    except Exception:
        return None

    if creation_date is None:
        return None

    now = datetime.now(timezone.utc)

    if creation_date.tzinfo is None:
        creation_date = creation_date.replace(tzinfo=timezone.utc)
    else:
        creation_date = creation_date.astimezone(timezone.utc)

    if creation_date > now:
        return None

    age_days = (now - creation_date).total_seconds() / 86400

    return round(age_days / 365.2425, 2)