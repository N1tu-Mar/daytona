"""Human sign-off (CLAUDE.md invariant #4).

Every approval hashes exactly what was approved, so a later dispute can
verify the signed content hasn't drifted from what's now on screen.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone


def content_hash(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def sign(actor: str, payload: dict) -> tuple[str, datetime, str]:
    """Returns (approved_by, approved_at, approval_hash)."""
    return actor, datetime.now(timezone.utc), content_hash(payload)
