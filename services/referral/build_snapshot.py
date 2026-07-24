"""Publish the prebuilt parsing snapshot to Daytona — the "cook once" step.

Run this ONCE, and again only when the parsing recipe in sandbox.py's
_parsing_image() changes (new OCR dep, etc.). It bakes the PDF/OCR toolchain
into a named Daytona snapshot so the referral pipeline can boot from it
instantly instead of rebuilding the image on every document.

    DAYTONA_API_KEY=... python -m services.referral.build_snapshot

When it prints "published", point the pipeline at the snapshot so boots skip
the declarative build entirely:

    export DAYTONA_SANDBOX_SNAPSHOT=meridian-parse:1

Recipe analogy: sandbox.py's _parsing_image() is the recipe card; this script
cooks it once and freezes the finished meal under a name; the pipeline then
just reheats that frozen meal per document. Same OS, no cooking in the
request path. See services/referral/sandbox.py for the boot side.

This script only publishes an image — it never touches a referral document,
so it needs no lockdown of its own.
"""

from __future__ import annotations

import os
import sys

from services.referral.sandbox import DEFAULT_SNAPSHOT_NAME, _parsing_image


def main() -> int:
    api_key = os.environ.get("DAYTONA_API_KEY")
    if not api_key:
        print(
            "DAYTONA_API_KEY not set — nothing to publish. "
            "The pipeline still runs without a snapshot (declarative build).",
            file=sys.stderr,
        )
        return 1

    from daytona import CreateSnapshotParams, Daytona, DaytonaConfig, Resources

    # Honor an override so you can cut a new version (":2", ":3") without
    # editing code, but default to the canonical name the boot path expects.
    name = os.environ.get("DAYTONA_SANDBOX_SNAPSHOT", DEFAULT_SNAPSHOT_NAME)
    client = Daytona(DaytonaConfig(api_key=api_key))

    print(
        f"Building snapshot {name!r} "
        "(Debian + pypdf/pillow/pytesseract + tesseract-ocr). "
        "First build is slow; that's the point — it happens here, once, not "
        "in the request path."
    )
    client.snapshot.create(
        CreateSnapshotParams(
            name=name,
            image=_parsing_image(),
            resources=Resources(cpu=1, memory=1),
        ),
        on_logs=lambda line: print(f"  {line}"),
    )
    print(f"\npublished {name}")
    print(f"Now set:  export DAYTONA_SANDBOX_SNAPSHOT={name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
