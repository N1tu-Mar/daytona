"""LLM extraction: messy referral text -> ReferralFeatures. Perception only.

This is the only place an LLM is allowed to touch triage data, and it never
decides urgency — it emits structured facts that app.rule_engine then
evaluates deterministically (CLAUDE.md: "LLMs extract. Rules decide.").

Every LLM call returns a Pydantic model (ReferralFeatures), no free-form
string parsing. On timeout, error, or a response that fails validation, this
raises ExtractionError — callers must treat that as ESCALATE, never as a
guess (CLAUDE.md invariant #3).
"""

from __future__ import annotations

import json
import logging
import os
import time

import httpx

from app.schemas import ReferralFeatures
from app.tracing import log_span, traced

log = logging.getLogger("meridian.referral.extract")

FIREWORKS_API_KEY = os.environ.get("FIREWORKS_API_KEY")
# Default chosen empirically — evals/extraction_ab.py diffs candidate models
# in Braintrust on the synthetic referral set. deepseek-v4-flash beat
# deepseek-v4-pro on verdict_preserved (0.69 vs 0.60) at ~16x lower latency
# (1.3s vs 21s/referral) with identical 100% extraction_escalation_safety,
# and pro's long reasoning traces caused timeouts. Fast AND safer-in-practice.
FIREWORKS_MODEL = os.environ.get("FIREWORKS_MODEL", "accounts/fireworks/models/deepseek-v4-flash")
FIREWORKS_URL = "https://api.fireworks.ai/inference/v1/chat/completions"
# Large reasoning models can take >15s to first byte; a timeout still fails
# safe (ExtractionError -> ESCALATE), this just stops us escalating referrals
# that a slightly slower-but-correct extraction would have handled.
TIMEOUT_SECONDS = float(os.environ.get("FIREWORKS_TIMEOUT_S", "60"))

EXTRACTION_FEATURES = [
    "age",
    "rectal_bleeding",
    "bleeding_duration_weeks",
    "change_in_bowel_habit",
    "bowel_habit_duration_weeks",
    "unintentional_weight_loss",
    "abdominal_pain",
    "iron_deficiency_anemia",
    "fit_result",
    "family_history_crc",
    "abdominal_or_rectal_mass",
    "prior_colonoscopy_date",
]

SYSTEM_PROMPT = """You extract structured clinical intake facts from a GI referral document.
You do not diagnose, assess likelihood of any condition, or suggest urgency — you only
report what is explicitly stated in the text.

Return ONLY a JSON object with these exact keys: age (int or null), rectal_bleeding
(bool or null), bleeding_duration_weeks (int or null), change_in_bowel_habit (bool or
null), bowel_habit_duration_weeks (int or null), unintentional_weight_loss (bool or
null), abdominal_pain (bool or null), iron_deficiency_anemia (bool or null), fit_result
("positive"/"negative"/"not_done" or null), family_history_crc ("none"/"first_degree"/
"multiple" or null), abdominal_or_rectal_mass (bool or null), prior_colonoscopy_date
(ISO date string or null), source_refs (object mapping each non-null field above to the
exact quote or line from the text it came from), extraction_confidence (object mapping
each non-null field above to a float 0.0-1.0).

If a fact is not stated, its value is null and it must not appear in source_refs or
extraction_confidence. Never infer a value that isn't explicitly stated. Never include
any diagnosis, condition name, or clinical judgment in your output."""


class ExtractionError(Exception):
    """Raised on timeout, API error, or a response that fails schema validation.
    Callers must treat this as ESCALATE, never fall back to a guess."""


@traced
def extract_features(raw_text: str, model: str | None = None) -> ReferralFeatures:
    """`model` overrides FIREWORKS_MODEL for one call — used by the
    extraction A/B eval (evals/extraction_ab.py) to compare models on the
    same dataset; production callers leave it None."""
    if not raw_text or not raw_text.strip():
        raise ExtractionError("empty referral text")

    if not FIREWORKS_API_KEY:
        raise ExtractionError(
            "FIREWORKS_API_KEY not configured — extraction cannot run. "
            "Set the env var, or use services/referral/pipeline.py's synthetic "
            "feature path for demo referrals that already have known features."
        )

    payload = {
        "model": model or FIREWORKS_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": raw_text},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0,
        # Reasoning models (e.g. deepseek) spend tokens on reasoning_content
        # BEFORE the JSON answer; 1024 truncated the JSON mid-field
        # (finish_reason=length). This cap covers reasoning + full answer.
        "max_tokens": int(os.environ.get("FIREWORKS_MAX_TOKENS", "8192")),
    }
    headers = {"Authorization": f"Bearer {FIREWORKS_API_KEY}", "Content-Type": "application/json"}

    start = time.monotonic()
    try:
        resp = httpx.post(FIREWORKS_URL, json=payload, headers=headers, timeout=TIMEOUT_SECONDS)
        resp.raise_for_status()
    except httpx.TimeoutException as e:
        raise ExtractionError(f"fireworks call timed out after {TIMEOUT_SECONDS}s") from e
    except httpx.HTTPError as e:
        raise ExtractionError(f"fireworks call failed: {e}") from e
    latency = time.monotonic() - start

    try:
        choice = resp.json()["choices"][0]
        if choice.get("finish_reason") == "length":
            # Truncated mid-JSON — parsing would either fail or, worse,
            # silently drop trailing fields. Fail safe instead.
            raise ExtractionError("fireworks response truncated (finish_reason=length)")
        content = (choice["message"]["content"] or "").strip()
        parsed = json.loads(content)
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        raise ExtractionError(f"malformed fireworks response: {e}") from e

    try:
        features = ReferralFeatures.model_validate(parsed)
    except Exception as e:
        raise ExtractionError(f"extraction failed schema validation: {e}") from e

    log.info(
        "extraction_complete",
        extra={"latency_s": round(latency, 2), "fields_populated": len(features.source_refs)},
    )
    log_span(
        metadata={
            "model": model or FIREWORKS_MODEL,
            "latency_s": round(latency, 2),
            "fields_populated": len(features.source_refs),
            "usage": resp.json().get("usage"),
        }
    )
    return features
