"""Unit tests for the Daytona sandbox lifecycle, with the SDK client mocked.

No network and no real key: we inject a fake Daytona client so we can assert
the failure envelope precisely.

  (a) the sandbox is always torn down — client.delete() runs even when
      code_run raises;
  (b) every sandbox problem (non-zero exit, unparseable output, creation
      failure, in-box exception) surfaces as SandboxError — which
      pipeline.py already converts to an ESCALATE verdict (not asserted
      here; pipeline.py is intentionally left untouched);
  (c) once a key is configured, the unsandboxed local decode is never
      reachable.

Note: SDK 0.200 tears sandboxes down via client.delete(); there is no
remove(). These tests assert delete() accordingly.
"""

from __future__ import annotations

import json

import daytona
import pytest

from services.referral import sandbox as sb


class _FakeProcess:
    def __init__(self, code_run):
        self._code_run = code_run

    def code_run(self, code, timeout=None):
        return self._code_run(code, timeout)


class _FakeSandbox:
    def __init__(self, process, sandbox_id="ds-test-abc123"):
        self.id = sandbox_id
        self.process = process


class _FakeClient:
    def __init__(self, calls, code_run, create_error=None):
        self._calls = calls
        self._code_run = code_run
        self._create_error = create_error

    def create(self, params=None, timeout=None):
        self._calls["created"] += 1
        if self._create_error:
            raise self._create_error
        return _FakeSandbox(_FakeProcess(self._code_run))

    def delete(self, sandbox, timeout=60, wait=False):
        self._calls["deleted"] += 1


class _Resp:
    """Stand-in for daytona's ExecuteResponse."""

    def __init__(self, exit_code, result):
        self.exit_code = exit_code
        self.result = result


@pytest.fixture
def wired(monkeypatch):
    """Configure a key, stub the (network-touching) params/image build, and
    make any call into the local-decode fallback a hard failure."""
    monkeypatch.setattr(sb, "DAYTONA_API_KEY", "dtn_fake_key")
    monkeypatch.setattr(sb, "_sandbox_params", lambda: None)
    monkeypatch.setattr(daytona, "DaytonaConfig", lambda **kw: object())

    def _forbidden(*a, **k):
        raise AssertionError("local decode must not run when a key is set")

    monkeypatch.setattr(sb, "_decode_locally_unsandboxed", _forbidden)
    return monkeypatch


def _install_client(monkeypatch, calls, code_run, create_error=None):
    client = _FakeClient(calls, code_run, create_error)
    monkeypatch.setattr(daytona, "Daytona", lambda config: client)
    return client


# (a) teardown always runs -------------------------------------------------


def test_teardown_runs_even_when_code_run_raises(wired):
    calls = {"created": 0, "deleted": 0}

    def boom(code, timeout):
        raise RuntimeError("kaboom inside code_run")

    _install_client(wired, calls, boom)

    with pytest.raises(sb.SandboxError):
        sb.parse_document_in_sandbox(b"anything", "referral.pdf")

    assert calls["created"] == 1
    assert calls["deleted"] == 1  # delete() ran despite the error


# (b) errors surface as SandboxError --------------------------------------


def test_nonzero_exit_is_sandbox_error(wired):
    calls = {"created": 0, "deleted": 0}
    _install_client(wired, calls, lambda code, timeout: _Resp(1, "traceback..."))
    with pytest.raises(sb.SandboxError):
        sb.parse_document_in_sandbox(b"x", "r.pdf")
    assert calls["deleted"] == 1


def test_unparseable_output_is_sandbox_error(wired):
    calls = {"created": 0, "deleted": 0}
    _install_client(wired, calls, lambda code, timeout: _Resp(0, "this is not json"))
    with pytest.raises(sb.SandboxError):
        sb.parse_document_in_sandbox(b"x", "r.pdf")
    assert calls["deleted"] == 1


def test_create_failure_is_sandbox_error(wired):
    calls = {"created": 0, "deleted": 0}
    _install_client(
        wired,
        calls,
        lambda code, timeout: _Resp(0, "{}"),
        create_error=RuntimeError("no capacity"),
    )
    with pytest.raises(sb.SandboxError):
        sb.parse_document_in_sandbox(b"x", "r.pdf")
    assert calls["created"] == 1
    assert calls["deleted"] == 0  # create never returned a box to tear down


# (c) with a key set, local decode is never invoked -----------------------


def test_success_returns_provenance_and_never_local_decodes(wired):
    calls = {"created": 0, "deleted": 0}
    _install_client(
        wired,
        calls,
        lambda code, timeout: _Resp(0, json.dumps({"text": "PARSED TEXT"})),
    )

    result = sb.parse_document_in_sandbox(b"x", "r.pdf")

    assert result.text == "PARSED TEXT"
    assert result.sandboxed is True
    assert result.sandbox_id == "ds-test-abc123"
    assert result.duration_ms is not None
    assert calls["deleted"] == 1
    # Reaching here proves (c): _decode_locally_unsandboxed was patched to
    # raise if called, and it never fired.


def test_no_key_falls_back_to_local_decode():
    # Separate from `wired`: no key configured -> the fallback IS the path.
    import services.referral.sandbox as fresh

    orig = fresh.DAYTONA_API_KEY
    fresh.DAYTONA_API_KEY = None
    try:
        result = fresh.parse_document_in_sandbox(b"hello world", "note.txt")
    finally:
        fresh.DAYTONA_API_KEY = orig

    assert result.sandboxed is False
    assert result.sandbox_id is None
    assert result.text == "hello world"
