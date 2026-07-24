"""Turn call transcripts into playable voiced turns for the UI.

Pure assembly: the call flows in services/intake and services/ivr stay
audio-free and deterministic; this module decorates their finished
transcripts with audio so the frontend can play the call back turn by turn.
Any turn whose synthesis fails carries audio=None and renders as text —
a partial voice outage degrades a call to captions, never to an error.
"""

from __future__ import annotations

import base64

from services.voice.dtmf import dtmf_wav
from services.voice.tts import VOICE_IVR, VOICE_PATIENT, synthesize, synthesize_agent_line


def _b64(audio: bytes | None) -> str | None:
    return base64.b64encode(audio).decode() if audio else None


def voice_intake_turns(turns: list[dict]) -> list[dict]:
    """[{speaker, text}] -> same turns plus audio_b64/mime.

    Agent lines go through synthesize_agent_line (output filter enforced at
    the synthesizer); the simulated patient side uses a distinct voice so
    the played-back call is audibly two people.
    """
    voiced = []
    for turn in turns:
        if turn["speaker"] == "agent":
            audio = synthesize_agent_line(turn["text"])
        else:
            audio = synthesize(turn["text"], VOICE_PATIENT)
        voiced.append({**turn, "audio_b64": _b64(audio), "mime": "audio/mpeg"})
    return voiced


def voice_ivr_transcript(transcript: list[str]) -> list[dict]:
    """Mock-IVR transcript lines -> voiced turns.

    "IVR: ..." lines get the payer's synthesized voice; "CALLER: ..." lines
    are DTMF keypresses, rendered as real touch-tones (locally generated
    WAV, no API call). Hold-music markers stay text-only.
    """
    voiced = []
    for line in transcript:
        if line.startswith("IVR: "):
            text = line[len("IVR: "):]
            audio = synthesize(text, VOICE_IVR)
            voiced.append({"speaker": "ivr", "text": text, "audio_b64": _b64(audio), "mime": "audio/mpeg"})
        elif line.startswith("CALLER: "):
            digits = line[len("CALLER: "):]
            audio = dtmf_wav(digits)
            voiced.append({"speaker": "caller", "text": digits, "audio_b64": _b64(audio), "mime": "audio/wav"})
        else:
            voiced.append({"speaker": "system", "text": line, "audio_b64": None, "mime": None})
    return voiced
