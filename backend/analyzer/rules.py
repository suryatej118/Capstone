
import re
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class TriggeredRule:
    rule_id: str
    description: str
    span: str
    weight: int
    start: int
    end: int


@dataclass
class Rule:
    rule_id: str
    description: str
    severity: str
    weight: int
    matcher: Callable[[str], Optional[re.Match]]


def regex_match(pattern: str) -> Callable[[str], Optional[re.Match]]:
    compiled = re.compile(pattern, re.IGNORECASE)

    def matcher(text: str) -> Optional[re.Match]:
        return compiled.search(text)

    return matcher


# R01 - Recruitment-related payment demands.
# Does not require a currency amount for common recruitment scams.


R01_PATTERN = (
    r"(?:"
    # Specific recruitment fee followed by an amount.
    r"\b(?:registration|processing|onboarding|verification|"
    r"interview|training|security|application|joining)\b"
    r"(?:\s+\w+){0,5}\s+fee\b"
    r".{0,60}(?:₹\s?|Rs\.?\s?|INR\s?)"
    r"\d[\d,]*(?:\.\d{1,2})?"

    r"|"

    # Amount followed by a named recruitment fee.
    r"(?:₹\s?|Rs\.?\s?|INR\s?)"
    r"\d[\d,]*(?:\.\d{1,2})?"
    r".{0,50}\b(?:registration|processing|onboarding|"
    r"verification|interview|training|security|application|joining)"
    r"\s+fee\b"

    r"|"

    # Generic payment instruction and recruitment fee.
    r"\b(?:pay|payment|transfer|send|deposit|purchase|buy|remit|wire)\b"
    r".{0,100}\b(?:fee|charge|deposit|registration|interview|"
    r"shortlisting|processing|verification|activation|equipment|shipping|"
    r"courier|training|certificate|access|booking|security)\b"

    r"|"

    r"\b(?:fee|charge|deposit|payment)\b.{0,100}\b(?:pay|transfer|send|"
    r"purchase|buy|required|requires|must|interview|shortlisting|"
    r"processing|verification|activation|equipment|shipping|courier|"
    r"training|certificate|access)\b"

    r"|"

    r"\b(?:buy|purchase)\b.{0,80}\b(?:gift cards?|vouchers?)\b"

    r"|"

    r"\b(?:gift cards?|vouchers?)\b.{0,80}\b"
    r"(?:redeem|redemption codes?|send|share|payment)\b"

    r")"
)


def match_r01(text: str) -> Optional[re.Match]:
    """
    Prioritize explicit recruitment fee demands.
    Ignore matches inside sentences that explicitly deny payment.
    """

    if not text:
        return None

    # Mask sentences that explicitly state no payment or fee is required.
    # Spaces preserve the original character positions for highlighting.
    masked_text = list(text)

    negative_pattern = re.compile(
        r"(?i)(?:^|(?<=[.!?;\n])\s*)"
        r"[^.!?;\n]*(?:"
        r"\bno\s+(?:registration\s+)?(?:fee|payment|charge)\b"
        r"|"
        r"\b(?:fee|payment|charge)\s+is\s+not\s+required\b"
        r"|"
        r"\bnot\s+required\s+to\s+pay\b"
        r"|"
        r"\bno\s+payment\s+is\s+required\b"
        r"|"
        r"\b(?:never|should\s+never|do\s+not|don't|should\s+not)\s+"
        r"(?:\w+\s+){0,4}"
        r"(?:pay|transfer|send|deposit|remit)\b"
        r")[^.!?;\n]*(?:[.!?;\n]|$)"
    )

    for negative_match in negative_pattern.finditer(text):
        for index in range(
            negative_match.start(),
            negative_match.end()
        ):
            masked_text[index] = " "

    searchable_text = "".join(masked_text)

    # First preference: named recruitment fee and its amount.
    specific_fee_pattern = re.compile(
        r"\b(?:registration|processing|onboarding|verification|"
        r"interview|training|security|application|joining)\b"
        r".{0,100}?\bfee\b"
        r".{0,60}?"
        r"(?:₹\s*|Rs\.?\s*|INR\s*)"
        r"\d[\d,]*(?:\.\d{1,2})?",
        re.IGNORECASE | re.DOTALL,
    )

    match = specific_fee_pattern.search(searchable_text)

    if match:
        return match

    # Fall back to the existing generic R01 pattern.
    return re.search(
        R01_PATTERN,
        searchable_text,
        re.IGNORECASE | re.DOTALL
    )


# R02 - Sensitive information requests.
# The matcher first looks for a request to disclose sensitive information.
# Safety warnings that merely mention OTPs or passwords should not trigger R02.
R02_PATTERN = (
    r"\b(?:"
    r"send|share|provide|submit|reveal|disclose|tell|forward|"
    r"enter|text|message|email|upload"
    r")\b[^.!?,;:?\n]{0,100}?\b(?:"
    r"aadhaar|pan|otp|one[-\s]?time password|"
    r"bank account(?:\s+number)?|ifsc|account no|account number|"
    r"banking password|online banking password|"
    r"debit card cvv|card security code|"
    r"cvv|upi pin|bank password"
    r")\b"
)

R02_WARNING_PATTERNS = [
    r"\bnever\s+(?:share|send|disclose|reveal|provide|give)\b",
    r"\bnever\s+(?:transfer|pay|send|share).{0,120}"
    r"\b(?:share|send|disclose|provide|give)\b",
    r"\bdo\s+not\s+(?:share|send|disclose|reveal|provide|give)\b",
    r"\bdon't\s+(?:share|send|disclose|reveal|provide|give)\b",
    r"\bshould\s+never\s+(?:share|send|disclose|reveal|provide|give)\b",
    r"\bshould\s+not\s+(?:share|send|disclose|reveal|provide|give)\b",
]


def _is_sensitive_warning(text: str, match: re.Match) -> bool:
    sentence_start = max(
        text.rfind(separator, 0, match.start())
        for separator in ".!?;\n"
    ) + 1
    sentence_end_candidates = [
        text.find(separator, match.end())
        for separator in ".!?;\n"
        if text.find(separator, match.end()) >= 0
    ]
    sentence_end = min(sentence_end_candidates, default=len(text))
    context = text[sentence_start:sentence_end]
    match_offset = match.start() - sentence_start
    prefix = context[:match_offset]
    negations = list(re.finditer(
        r"\b(?:never|do\s+not|don't|should\s+never|should\s+not)\b",
        prefix,
        re.IGNORECASE,
    ))
    if not negations:
        return False

    last_negation = negations[-1]
    between = prefix[last_negation.end():]
    if re.search(r"\b(?:but|however|except|unless)\b", between, re.IGNORECASE):
        return False

    return any(
        re.search(pattern, context, re.IGNORECASE)
        for pattern in R02_WARNING_PATTERNS
    )


def match_r02(text: str) -> Optional[re.Match]:
    """Return the first R02 request that is not a safety disclaimer."""
    for match in re.finditer(R02_PATTERN, text, re.IGNORECASE):
        if not _is_sensitive_warning(text, match):
            return match
    return None



# R03 - Explicit monetary transfer / UPI destination.
# Do not treat ordinary email addresses as UPI IDs.

R03_PATTERN = (
    r"(?:"
    # Payment instruction followed by a currency amount.
    r"\b(?:pay|transfer|send|deposit|remit)\b"
    r"(?:[^\S\r\n]+\w+){0,6}[^\S\r\n]+"
    r"(?:₹\s?|\bINR\s?|\bRs\.?\s?)"
    r"\d[\d,]*(?:\.\d{1,2})?"
    r"|"
    # Explicitly labelled UPI ID.
    r"\bUPI(?:\s+(?:ID|address))?"
    r"\s*(?:is|:|=|-)?\s*"
    r"[A-Za-z0-9._-]{2,}@[A-Za-z]{2,}\b"
    r")"
)



# R04 - Urgency / pressure.

R04_PATTERN = (
    r"\b(?:limited seats|immediate joining|urgent|today only|"
    r"ASAP|within \d+ minutes?|expires in \d+ minutes?|"
    r"right away|apply within \d+ hours?|"
    r"only \d+ vacancies? remaining)\b"
)



# R05 - Suspicious links / domains.
R05_PATTERN = (
    r"(?:"
    r"https?://[^\s/]*\.(?:ru|xyz|info|club|tk|ml|gq|cf)\b"
    r"|https?://\d+\.\d+\.\d+\.\d+"
    r"|\b(?:bit\.ly|tinyurl|goo\.gl|t\.co)/?\S*"
    r")"
)


# R08 - Generic promises / unrealistic salary.
R08_PATTERN = (
    r"\b(?:high pay|work from home and earn|no experience required|"
    r"guaranteed salary|guaranteed placement|guaranteed job|"
    r"selection guaranteed)\b"
)


# R10 - Personal contact information.
R10_PATTERN = (
    r"(?:"
    r"\b(?:\+91[-\s]?)?[6-9]\d{9}\b"
    r"|"
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
    r")"
)


RULES = [
    Rule(
        rule_id="R01",
        description="Fee/payment request in hiring context",
        severity="HIGH",
        weight=30,
        matcher=match_r01,
    ),
    Rule(
        rule_id="R02",
        description="Request for sensitive personal/banking details",
        severity="HIGH",
        weight=30,
        matcher=match_r02,
    ),
    Rule(
        rule_id="R03",
        description="Request for monetary transfers or UPI",
        severity="HIGH",
        weight=25,
        matcher=regex_match(R03_PATTERN),
    ),
    Rule(
        rule_id="R04",
        description="Urgency / pressure language",
        severity="MEDIUM",
        weight=15,
        matcher=regex_match(R04_PATTERN),
    ),
    Rule(
        rule_id="R05",
        description="Suspicious link / unofficial domain pattern",
        severity="MEDIUM",
        weight=20,
        matcher=regex_match(R05_PATTERN),
    ),
    Rule(
        rule_id="R08",
        description="Overly generic job promises / unrealistic salary",
        severity="LOW",
        weight=5,
        matcher=regex_match(R08_PATTERN),
    ),
    Rule(
        rule_id="R10",
        description="Personal contact info present",
        severity="LOW",
        weight=1,
        matcher=regex_match(R10_PATTERN),
    ),
]


# Text rules total 126; context rules total 28.
TOTAL_RULE_WEIGHT = 154


def analyze_rules(
    text: str,
    *,
    contact_channel_mismatch: Optional[str] = None,
    is_duplicate: bool = False,
    uppercase_ratio: Optional[float] = None,
) -> tuple[int, list[TriggeredRule]]:
    """Return a normalized rule score and the triggered rules."""

    triggered: list[TriggeredRule] = []
    score_sum = 0

    for rule in RULES:
        match = rule.matcher(text)

        if match:
            triggered.append(
                TriggeredRule(
                    rule_id=rule.rule_id,
                    description=rule.description,
                    span=match.group(0),
                    weight=rule.weight,
                    start=match.start(),
                    end=match.end(),
                )
            )
            score_sum += rule.weight

    # R06 - Contact channel mismatch.
    if contact_channel_mismatch:
        start = text.find(contact_channel_mismatch)
        triggered.append(
            TriggeredRule(
                rule_id="R06",
                description="Contact channel mismatch / unofficial recruiter handles",
                span=contact_channel_mismatch,
                weight=15,
                start=start,
                end=start + len(contact_channel_mismatch) if start >= 0 else -1,
            )
        )
        score_sum += 15

    # R07 - Reposting / near-duplicate.
    if is_duplicate:
        triggered.append(
            TriggeredRule(
                rule_id="R07",
                description="Reposting / near-duplicate marker",
                span="duplicate report detected",
                weight=10,
                start=-1,
                end=-1,
            )
        )
        score_sum += 10

    # R09 - Excessive uppercase usage.
    if uppercase_ratio is not None and uppercase_ratio >= 0.30:
        triggered.append(
            TriggeredRule(
                rule_id="R09",
                description="Poor grammar / excessive uppercase usage",
                span="excessive uppercase usage",
                weight=3,
                start=-1,
                end=-1,
            )
        )
        score_sum += 3

    rule_score = min(100, round((score_sum / TOTAL_RULE_WEIGHT) * 100))
    return rule_score, triggered
