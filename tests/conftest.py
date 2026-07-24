"""Test isolation.

Every test run gets a fresh throwaway SQLite database instead of the demo's
meridian.db. Without this, tests that insert fixed row IDs (e.g. the intake
demo calls "demo-call-silent" et al.) collide with rows left by a previous
run — an IntegrityError — and they also pollute the real demo database.

The env var must be set BEFORE app.db is imported anywhere, so it lives at
module import time here: pytest loads conftest.py before collecting any test
module, and app.db reads MERIDIAN_DB_URL when its engine is first created.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

_TEST_DB = Path(tempfile.gettempdir()) / "meridian_test.db"
# Start each session from a clean slate.
if _TEST_DB.exists():
    _TEST_DB.unlink()
os.environ["MERIDIAN_DB_URL"] = f"sqlite:///{_TEST_DB}"

import pytest

from app.db import init_db


@pytest.fixture(scope="session", autouse=True)
def _isolated_db():
    init_db()
    yield
    if _TEST_DB.exists():
        _TEST_DB.unlink()
