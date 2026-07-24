"""Patient-facing output filter. Invariant #2: no diagnostic language, ever.

Runs on every patient-facing string and every generated document. Fail-closed:
if the filter itself errors, the message does not send.
"""

from __future__ import annotations

import logging
import re

log = logging.getLogger("meridian.output_filter")

CONDITION_TERMS = [
    "cancer",
    "carcinoma",
    "tumor",
    "tumour",
    "malignancy",
    "malignant",
    "crohn's",
    "crohns",
    "crohn",
    "colitis",
    "ibd",
    "ibs",
    "hemorrhoid",
    "hemorrhoids",
    "haemorrhoid",
    "haemorrhoids",
    "diverticulitis",
    "diverticulosis",
    "polyp",
    "polyps",
    "adenoma",
    "neoplasm",
]

REASSURANCE_PATTERNS = [
    r"probably\s+nothing",
    r"unlikely\s+to\s+be",
    r"don'?t\s+worry",
    r"nothing\s+to\s+worry",
    r"not\s+serious",
    r"wait\s+and\s+see",
    r"should\s+be\s+fine",
    r"no\s+need\s+to\s+worry",
    r"probably\s+(just|benign)",
    r"it'?s\s+(probably|likely)\s+(just\s+)?\w+",
    r"you'?re\s+(probably\s+)?fine",
    r"\bbenign\b",
    r"\bharmless\b",
]

_CONDITION_RE = re.compile(
    r"\b(" + "|".join(re.escape(t) for t in CONDITION_TERMS) + r")\b",
    re.IGNORECASE,
)
_REASSURANCE_RE = re.compile("|".join(REASSURANCE_PATTERNS), re.IGNORECASE)
_PROBABILITY_RE = re.compile(
    r"\b\d{1,3}\s?%\s+(chance|likely|probability|risk)\b"
    r"|\b(chance|probability|risk|likelihood)\s+(of|that)\s+it'?s?\s+being\b",
    re.IGNORECASE,
)


class OutputFilterError(Exception):
    """Raised when the filter itself fails. Treat as fail-closed: don't send."""


class FilterResult:
    def __init__(self, allowed: bool, reasons: list[str]):
        self.allowed = allowed
        self.reasons = reasons


def check_output(text: str) -> FilterResult:
    """Return whether `text` is safe to show/send to a patient.

    Fail-closed: any exception here is caught by the caller (send_patient_message)
    and treated as blocked, never as allowed.
    """
    if text is None:
        raise OutputFilterError("output_filter received None")

    reasons: list[str] = []

    m = _CONDITION_RE.search(text)
    if m:
        reasons.append(f"condition_term:{m.group(0).lower()}")

    m = _REASSURANCE_RE.search(text)
    if m:
        reasons.append(f"reassurance_pattern:{m.group(0).lower()}")

    m = _PROBABILITY_RE.search(text)
    if m:
        reasons.append(f"probability_statement:{m.group(0).lower()}")

    return FilterResult(allowed=len(reasons) == 0, reasons=reasons)


def send_patient_message(text: str) -> str | None:
    """The only sanctioned way to emit patient-facing text.

    Returns the text if it passes the filter, otherwise None. Never raises:
    any failure in the filter itself blocks the message (fail-closed).
    """
    try:
        result = check_output(text)
    except Exception:
        log.exception("output_filter_error_fail_closed")
        return None

    if not result.allowed:
        log.warning("output_filter_blocked", extra={"reasons": result.reasons, "text": text})
        return None

    return text
