"""Voice layer tests — no ElevenLabs key, no network.

What must hold even with audio completely unavailable: the filter runs
inside the synthesizer (invariant #2 reaches the audio boundary), failures
degrade to text instead of erroring, and the disk cache means a demo rerun
never re-spends credits.
"""

from __future__ import annotations

import wave
from io import BytesIO

import httpx
import pytest

from services.voice import calls, dtmf, tts


@pytest.fixture(autouse=True)
def _isolated_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(tts, "CACHE_DIR", tmp_path / "voice_cache")
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)


def test_no_key_degrades_to_none():
    assert tts.synthesize("Hello", tts.VOICE_AGENT) is None


def test_agent_line_is_filtered_before_synthesis(monkeypatch):
    """A line containing a condition name must never reach the API."""
    sent_texts = []

    def fake_post(url, headers=None, json=None, timeout=None):
        sent_texts.append(json["text"])
        return httpx.Response(200, content=b"mp3bytes", request=httpx.Request("POST", url))

    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")
    monkeypatch.setattr(tts.httpx, "post", fake_post)

    audio = tts.synthesize_agent_line("It's probably just hemorrhoids, don't worry.")
    assert audio == b"mp3bytes"
    assert len(sent_texts) == 1
    lowered = sent_texts[0].lower()
    assert "hemorrhoid" not in lowered
    assert "worry" not in lowered


def test_api_error_returns_none_not_raise(monkeypatch):
    def fake_post(url, **kwargs):
        raise httpx.ConnectError("no network")

    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")
    monkeypatch.setattr(tts.httpx, "post", fake_post)
    assert tts.synthesize("Hello", tts.VOICE_AGENT) is None


def test_cache_hit_skips_api(monkeypatch):
    call_count = 0

    def fake_post(url, headers=None, json=None, timeout=None):
        nonlocal call_count
        call_count += 1
        return httpx.Response(200, content=b"audio", request=httpx.Request("POST", url))

    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")
    monkeypatch.setattr(tts.httpx, "post", fake_post)

    assert tts.synthesize("Can you tell me your age?", tts.VOICE_AGENT) == b"audio"
    assert tts.synthesize("Can you tell me your age?", tts.VOICE_AGENT) == b"audio"
    assert call_count == 1

    # cached audio is served even after the key disappears (quota story)
    monkeypatch.delenv("ELEVENLABS_API_KEY")
    assert tts.synthesize("Can you tell me your age?", tts.VOICE_AGENT) == b"audio"


def test_dtmf_generates_valid_wav_per_digit():
    audio = dtmf.dtmf_wav("3")
    assert audio is not None
    with wave.open(BytesIO(audio)) as w:
        assert w.getnchannels() == 1
        assert w.getframerate() == dtmf.SAMPLE_RATE
        assert w.getnframes() > 0

    ten_digits = dtmf.dtmf_wav("1234567890")
    assert ten_digits is not None
    assert len(ten_digits) > len(audio)


def test_dtmf_non_digits_return_none():
    assert dtmf.dtmf_wav("hello") is None
    assert dtmf.dtmf_wav("") is None


def test_voice_intake_turns_degrade_without_key():
    turns = [
        {"speaker": "agent", "text": "Can you tell me your age?"},
        {"speaker": "patient", "text": "I'm 42"},
    ]
    voiced = calls.voice_intake_turns(turns)
    assert [t["text"] for t in voiced] == [t["text"] for t in turns]
    assert all(t["audio_b64"] is None for t in voiced)


def test_voice_ivr_transcript_shapes():
    transcript = [
        "IVR: Thank you for calling Payer Health Services.",
        "CALLER: 3",
        "CALLER: 1234567890",
    ]
    voiced = calls.voice_ivr_transcript(transcript)
    assert voiced[0]["speaker"] == "ivr"
    assert voiced[0]["audio_b64"] is None  # no key -> text-only
    # DTMF is local synthesis: audio present even with no API key
    assert voiced[1]["speaker"] == "caller"
    assert voiced[1]["audio_b64"] is not None
    assert voiced[1]["mime"] == "audio/wav"
    assert voiced[2]["audio_b64"] is not None
