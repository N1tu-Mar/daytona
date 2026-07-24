"""Real DTMF keypad tones for the IVR call audio, generated locally.

The caller side of a payer IVR call isn't speech — it's touch-tones. These
are the actual ITU dual-tone frequency pairs, synthesized as WAV in pure
Python (stdlib only), so keypresses in the call playback sound like a real
phone and cost zero API credits.
"""

from __future__ import annotations

import io
import math
import struct
import wave

# ITU-T Q.23 low/high frequency pairs.
DTMF_FREQS: dict[str, tuple[int, int]] = {
    "1": (697, 1209), "2": (697, 1336), "3": (697, 1477),
    "4": (770, 1209), "5": (770, 1336), "6": (770, 1477),
    "7": (852, 1209), "8": (852, 1336), "9": (852, 1477),
    "*": (941, 1209), "0": (941, 1336), "#": (941, 1477),
}

SAMPLE_RATE = 8000  # narrowband, like a phone line
TONE_SECONDS = 0.14
GAP_SECONDS = 0.06
AMPLITUDE = 0.45  # of int16 full scale, split across the two tones


def dtmf_wav(digits: str) -> bytes | None:
    """WAV bytes for a digit sequence; None if it contains no DTMF digits.

    Non-DTMF characters are skipped rather than erroring — IVR transcripts
    label caller turns with raw input strings, and a hold/any-key turn
    ("*") and a member ID ("1234567890") should both just sound right.
    """
    keys = [d for d in digits if d in DTMF_FREQS]
    if not keys:
        return None

    frames = bytearray()
    tone_n = int(SAMPLE_RATE * TONE_SECONDS)
    gap_n = int(SAMPLE_RATE * GAP_SECONDS)
    peak = int(32767 * AMPLITUDE / 2)

    for key in keys:
        low, high = DTMF_FREQS[key]
        for i in range(tone_n):
            t = i / SAMPLE_RATE
            sample = peak * (math.sin(2 * math.pi * low * t) + math.sin(2 * math.pi * high * t))
            frames += struct.pack("<h", int(sample))
        frames += b"\x00\x00" * gap_n

    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(bytes(frames))
    return buf.getvalue()
