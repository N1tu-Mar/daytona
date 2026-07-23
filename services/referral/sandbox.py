"""Daytona-sandboxed document parsing.

Scanned referrals are attacker-controlled input, and PDF/OCR toolchains have
a long history of RCE. We don't run untrusted-document parsing (PDF/image
decoding, OCR) in the API process — it runs inside a throwaway Daytona
sandbox, and only the resulting plain text crosses back into our process.

This module owns exactly one job: given raw document bytes, return decoded
plain text, with the decode step isolated. It does NOT call the LLM
extractor — that happens afterward, outside the sandbox, on trusted text.
"""

from __future__ import annotations

import logging
import os

log = logging.getLogger("scoped.referral.sandbox")

DAYTONA_API_KEY = os.environ.get("DAYTONA_API_KEY")

# Runs inside the sandbox. Kept intentionally minimal: decode text-like
# documents directly, and OCR image/PDF documents via pytesseract/pypdf if
# available in the sandbox image. Never executes anything from the document
# itself — it only reads bytes.
_SANDBOX_SCRIPT = """
import base64, json, sys

payload = json.loads(sys.stdin.read())
data = base64.b64decode(payload["content_b64"])
filename = payload.get("filename", "")

def decode_text(data: bytes) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("latin-1", errors="replace")

text = ""
if filename.lower().endswith(".pdf"):
    try:
        from pypdf import PdfReader
        import io
        reader = PdfReader(io.BytesIO(data))
        text = "\\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception as e:
        text = ""
elif filename.lower().endswith((".png", ".jpg", ".jpeg", ".tiff")):
    try:
        import pytesseract
        from PIL import Image
        import io
        text = pytesseract.image_to_string(Image.open(io.BytesIO(data)))
    except Exception as e:
        text = ""
else:
    text = decode_text(data)

print(json.dumps({"text": text}))
"""


class SandboxError(Exception):
    """Raised when the sandbox can't be reached or parsing fails inside it.
    Callers must treat this as ESCALATE (invariant #3: document unparseable)."""


def parse_document_in_sandbox(content: bytes, filename: str) -> str:
    """Decode/OCR `content` inside a Daytona sandbox and return plain text.

    Falls back to local decoding ONLY when no Daytona credentials are
    configured, with a loud warning — that path exists so the demo still
    runs without a Daytona account, not because it's an acceptable
    production posture. In production this function must always route
    through the sandbox.
    """
    if not DAYTONA_API_KEY:
        log.warning(
            "daytona_not_configured_falling_back_to_local_decode",
            extra={"doc_filename": filename},
        )
        return _decode_locally_unsandboxed(content, filename)

    try:
        from daytona_sdk import Daytona, DaytonaConfig  # type: ignore[import-not-found]
    except ImportError as e:
        raise SandboxError("daytona_sdk not installed") from e

    import base64
    import json

    try:
        client = Daytona(DaytonaConfig(api_key=DAYTONA_API_KEY))
        sandbox = client.create()
        try:
            payload = json.dumps(
                {"content_b64": base64.b64encode(content).decode("ascii"), "filename": filename}
            )
            result = sandbox.process.code_run(_SANDBOX_SCRIPT, stdin=payload)
            if result.exit_code != 0:
                raise SandboxError(f"sandbox exited {result.exit_code}: {result.result}")
            output = json.loads(result.result)
            return output["text"]
        finally:
            client.remove(sandbox)
    except SandboxError:
        raise
    except Exception as e:
        raise SandboxError(f"daytona sandbox parse failed: {e}") from e


def _decode_locally_unsandboxed(content: bytes, filename: str) -> str:
    """Demo-only fallback. NOT the sandboxed path — see module docstring."""
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return content.decode("latin-1", errors="replace")
