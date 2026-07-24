"""ElevenLabs text-to-speech for the intake line and payer IVR calls.

The voice layer inherits invariant #2 instead of trusting its callers:
every agent-spoken line is re-run through the patient-facing output filter
*inside this module*, immediately before synthesis. Transcript text is
already filtered upstream (services/intake/call.py), but audio is the one
artifact a judge or patient actually hears, so the filter runs again at the
last possible moment — the synthesizer physically cannot receive a
diagnosis or reassurance. If the filter blocks or errors, the line is
synthesized as the standard fallback, fail-closed, same as text.

Degradation contract (CLAUDE.md: every integration degrades safely):
no ELEVENLABS_API_KEY, an API error, or exhausted quota all return None —
callers ship the text transcript without audio and nothing downstream
breaks. Synthesis is cached on disk by (voice, model, text) so a demo rerun
costs zero credits and returns instantly; the fixed-order question script
means almost every agent line is a cache hit after the first call.
"""

from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path

import httpx

from app.output_filter import send_patient_message

log = logging.getLogger("meridian.voice.tts")

ELEVENLABS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
# Flash is the cheapest/fastest model — right for short scripted lines, and
# it halves credit burn on the free/creator tiers used at the hackathon.
MODEL_ID = os.environ.get("ELEVENLABS_MODEL", "eleven_flash_v2_5")
TIMEOUT_SECONDS = float(os.environ.get("ELEVENLABS_TIMEOUT_S", "30"))

# Premade voices (available on every tier, so the demo never depends on a
# paid voice library): the intake agent should sound calm and clinical, the
# payer IVR corporate and flat, the simulated patient like a person.
VOICE_AGENT = "EXAVITQu4vr4xnSDxMaL"  # Sarah — mature, reassuring
VOICE_PATIENT = "iP95p4xoKVk53GoZ742B"  # Chris — down-to-earth
VOICE_IVR = "onwK4e9ZLuTAKqWW03F9"  # Daniel — steady broadcaster

CACHE_DIR = Path(__file__).parent.parent.parent / "data" / "voice_cache"

FALLBACK_LINE = (
    "I'm not able to get a clear answer on that. A nurse will call you back "
    "to finish getting you scheduled."
)


def _api_key() -> str | None:
    # Read at call time, not import time, so app/env.py's .env loading and
    # test monkeypatching both work regardless of import order.
    return os.environ.get("ELEVENLABS_API_KEY")


def _cache_path(voice_id: str, text: str) -> Path:
    digest = hashlib.sha256(f"{voice_id}|{MODEL_ID}|{text}".encode()).hexdigest()
    return CACHE_DIR / f"{digest}.mp3"


def synthesize(text: str, voice_id: str) -> bytes | None:
    """Raw synthesis: text -> mp3 bytes, or None if voice is unavailable.

    Never raises — an audio failure must not take down a call flow that is
    perfectly capable of completing as text.
    """
    if not text or not text.strip():
        return None

    cached = _cache_path(voice_id, text)
    if cached.exists():
        return cached.read_bytes()

    key = _api_key()
    if not key:
        return None

    try:
        resp = httpx.post(
            ELEVENLABS_URL.format(voice_id=voice_id),
            headers={"xi-api-key": key, "Content-Type": "application/json"},
            json={"text": text, "model_id": MODEL_ID},
            timeout=TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
    except httpx.HTTPError as e:
        log.warning("tts_failed_degrading_to_text", extra={"error": str(e), "voice_id": voice_id})
        return None

    audio = resp.content
    if not audio:
        return None

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cached.write_bytes(audio)
    log.info("tts_synthesized", extra={"voice_id": voice_id, "chars": len(text)})
    return audio


def synthesize_agent_line(text: str) -> bytes | None:
    """Synthesis for anything spoken *by the agent to a patient*.

    Re-applies the output filter before the text can reach the synthesizer
    (invariant #2, fail-closed). Already-safe text passes through unchanged;
    anything blocked is spoken as the fallback line instead of silence, so
    the caller is never left on a dead line.
    """
    safe = send_patient_message(text)
    return synthesize(safe or FALLBACK_LINE, VOICE_AGENT)
