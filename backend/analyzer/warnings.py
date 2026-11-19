"""Critical warning generation for high-severity detection evidence."""

from typing import Iterable

from backend.analyzer.rules import TriggeredRule


CRITICAL_WARNING_COPY = {
    "R01": (
        "Upfront recruitment payment",
        "The posting asks for a fee or payment in a hiring context.",
    ),
    "R02": (
        "Sensitive information request",
        "The posting asks for sensitive personal or banking information.",
    ),
    "R03": (
        "Monetary transfer request",
        "The posting asks for a transfer or payment destination.",
    ),
}


def get_critical_warnings(
    triggered_rules: Iterable[TriggeredRule],
) -> list[dict]:
    """
    Build prominent warnings for high-severity rule evidence.

    These warnings are independent of the hybrid score and risk level.
    Each warning includes the exact text span matched by the rule engine.
    """
    warnings = []
    for rule in triggered_rules:
        copy = CRITICAL_WARNING_COPY.get(rule.rule_id)
        if copy is None:
            continue

        title, message = copy
        warnings.append({
            "code": rule.rule_id,
            "title": title,
            "message": message,
            "evidence": rule.span,
        })

    return warnings
