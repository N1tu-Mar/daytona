"""Optional Braintrust tracing for the live pipelines.

Every referral upload and intake call produces a full trace in Braintrust
(project "meridian"): sandbox parse -> LLM extraction -> rule engine, with
the sandbox id, rules fired, and rule version attached to the spans. That
makes each production decision replayable and turns any surprising trace
into a future eval case.

Fail-open by design: without a BRAINTRUST_API_KEY (or the package), every
helper here is a no-op and the pipeline behaves identically. Tracing is
observability — it must never be able to break triage (the same reasoning
as invariant #3, applied to telemetry).
"""

from __future__ import annotations

import logging
import os

log = logging.getLogger("meridian.tracing")

try:
    import braintrust
    from braintrust import traced  # re-exported: @traced spans no-op without a logger

    _AVAILABLE = True
except ImportError:  # braintrust not installed — decorator becomes identity
    _AVAILABLE = False

    def traced(*d_args, **d_kwargs):  # type: ignore[misc]
        if len(d_args) == 1 and callable(d_args[0]) and not d_kwargs:
            return d_args[0]

        def deco(fn):
            return fn

        return deco


_initialized = False


def init_tracing() -> bool:
    """Start the Braintrust logger once, if configured. Safe to call often."""
    global _initialized
    if _initialized:
        return True
    if not _AVAILABLE or not os.environ.get("BRAINTRUST_API_KEY"):
        return False
    try:
        braintrust.init_logger(project="meridian")
    except Exception as e:  # bad key/network — run untraced rather than crash
        log.warning("braintrust_init_failed_running_untraced", extra={"error": str(e)})
        return False
    _initialized = True
    log.info("braintrust_tracing_enabled")
    return True


def log_span(**fields) -> None:
    """Attach input/output/metadata to the current span; no-op when off."""
    if not (_AVAILABLE and _initialized):
        return
    try:
        braintrust.current_span().log(**fields)
    except Exception:
        pass  # telemetry must never take down the pipeline
