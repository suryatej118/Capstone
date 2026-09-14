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

# ---------------------------------------------------------------------------
# Rule matching functions
# ---------------------------------------------------------------------------

def regex_match(pattern: str) -> Callable[[str], Optional[re.Match]]:
    compiled = re.compile(pattern, re.IGNORECASE)

    def matcher(text: str) -> Optional[re.Match]:
        return compiled.search(text)

    return matcher


# R01 - Fee/payment request
R01_PATTERN = (
    r"\b(pay|payment|fee|charge|deposit|registration|training)\b"
    r".{0,100}"
    r"\b(Rs\.?|₹|INR|\d{3,})\b"
)


# R02 - Sensitive personal/banking information
R02_PATTERN = (
    r"\b("
    r"aadhaar|pan|otp|one[-\s]?time|bank account|"
    r"ifsc|account no|account number"
    r")\b"
)


# R03 - Monetary transfer / UPI
R03_PATTERN = (
    r"("
    r"\b[0-9]{2,4}(\.[0-9]{1,2})?\s?(INR|Rs|₹)\b"
    r"|"
    r"\b[a-zA-Z0-9.\-_]{2,}@[a-zA-Z]{3,}\b"
    r")"
)


# R04 - Urgency / pressure
R04_PATTERN = (
    r"\b("
    r"apply now|limited seats|immediate joining|urgent|today only|ASAP"
    r")\b"
)


# R05 - Suspicious links / domains
R05_PATTERN = (
    r"("
    r"https?://[^\s/]*\.(ru|xyz|info|club|tk|ml|gq|cf)\b"
    r"|"
    r"https?://\d+\.\d+\.\d+\.\d+"
    r"|"
    r"\b(bit\.ly|tinyurl|goo\.gl)\b"
    r")"
)


# R08 - Generic promises / unrealistic salary
R08_PATTERN = (
    r"\b("
    r"high pay|work from home and earn|no experience required|"
    r"guaranteed salary"
    r")\b"
)


# R10 - Personal contact information
R10_PATTERN = (
    r"("
    # Phone number
    r"\b(?:\+91[-\s]?)?[6-9]\d{9}\b"
    r"|"
    # Email address
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
    r")"
)


# ---------------------------------------------------------------------------
# Rule definitions
# ---------------------------------------------------------------------------

RULES = [
    Rule(
        rule_id="R01",
        description="Fee/payment request in hiring context",
        severity="HIGH",
        weight=30,
        matcher=regex_match(R01_PATTERN),
    ),
    Rule(
        rule_id="R02",
        description="Early request for sensitive personal/banking details",
        severity="HIGH",
        weight=30,
        matcher=regex_match(R02_PATTERN),
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


# Total weight of all ten rules, including context-dependent rules.
TOTAL_RULE_WEIGHT = 154


# ---------------------------------------------------------------------------
# Rule engine
# ---------------------------------------------------------------------------

def analyze_rules(
    text: str,
    *,
    contact_channel_mismatch: Optional[str] = None,
    is_duplicate: bool = False,
    uppercase_ratio: Optional[float] = None,
) -> tuple[int, list[TriggeredRule]]:
    """
    Analyze job-post text using the MVP rule set.

    Returns:
        (rule_score, triggered_rules)

    Context-dependent rules:
        R06: contact_channel_mismatch
        R07: is_duplicate
        R09: uppercase_ratio

    These are optional because their required context comes from other
    parts of the application.
    """

    triggered: list[TriggeredRule] = []
    score_sum = 0

    # Text-based rules
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

    # R06 - Contact channel mismatch
    if contact_channel_mismatch:
        triggered.append(
            TriggeredRule(
                rule_id="R06",
                description="Contact channel mismatch / unofficial recruiter handles",
                span=contact_channel_mismatch,
                weight=15,
                start=text.find(contact_channel_mismatch),
                end=text.find(contact_channel_mismatch) + len(contact_channel_mismatch),
            )
        )
        score_sum += 15

    # R07 - Reposting / near-duplicate
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

    # R09 - Poor grammar / many ALL-CAPS words
    #
    # The project specification does not define the exact X threshold yet,
    # so uppercase_ratio is supplied by the caller rather than hard-coded.
    if uppercase_ratio is not None and uppercase_ratio > 0:
        # The exact threshold will be tuned during evaluation.
        # For now, this rule is triggered when the supplied heuristic
        # determines that the text contains excessive uppercase usage.
        if uppercase_ratio >= 0.30:
            triggered.append(
                TriggeredRule(
                    rule_id="R09",
                    description="Poor grammar / many ALL-CAPS words",
                    span="excessive uppercase usage",
                    weight=3,
                    start=-1,
                    end=-1,
                )
            )
            score_sum += 3

    rule_score = min(
        100,
        round((score_sum / TOTAL_RULE_WEIGHT) * 100),
    )

    return rule_score, triggered