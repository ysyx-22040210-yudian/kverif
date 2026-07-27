from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import pytest


ENGINE_PATH = Path(__file__).resolve().parents[2] / "tcl_engine" / "kdebug_engine.py"
SPEC = importlib.util.spec_from_file_location("kdebug_engine_under_test", ENGINE_PATH)
assert SPEC is not None and SPEC.loader is not None
ENGINE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ENGINE)


@pytest.mark.unit
def test_elab_db_uses_verdi_elab_argument() -> None:
    assert ENGINE.design_args_for_target({"elab_db": "/tmp/TB.elab++"}) == [
        "-elab",
        "/tmp/TB.elab++",
    ]
    assert ENGINE.target_mode({"elab_db": "/tmp/TB.elab++"}) == "design"


@pytest.mark.unit
def test_kdebug_home_override_and_legacy_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "user-home"
    configured = tmp_path / "isolated-kdebug-root"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("KDEBUG_HOME", raising=False)
    assert ENGINE.kdebug_home() == str(home / ".kdebug")

    monkeypatch.setenv("KDEBUG_HOME", str(configured))
    assert ENGINE.kdebug_home() == str(configured)
    assert ENGINE.engine_home() == str(configured / "engine")
    assert ENGINE.registry_path() == str(configured / "engine" / "registry.json")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("KDEBUG_HOME", "relative-kdebug-root")
    assert ENGINE.kdebug_home() == str(tmp_path / "relative-kdebug-root")


@pytest.mark.unit
def test_read_json_file_uses_utf8_and_preserves_default_on_decode_error(
    tmp_path: Path,
) -> None:
    unicode_text = chr(0x4E2D) + chr(0x6587)
    response_path = tmp_path / "response.json"
    response_path.write_bytes(
        ('{"message":"' + unicode_text + '"}').encode("utf-8")
    )
    assert ENGINE.read_json_file(str(response_path)) == {"message": unicode_text}

    response_path.write_bytes(b"\xff")
    fallback = {"fallback": True}
    assert ENGINE.read_json_file(str(response_path), fallback) is fallback


@pytest.mark.unit
def test_verdi_subprocess_timeout_supports_100_milliseconds() -> None:
    assert ENGINE.subprocess_timeout_seconds(
        {"limits": {"timeout_ms": 100}}, 120000
    ) == pytest.approx(0.1)
    assert ENGINE.subprocess_timeout_seconds(
        {"limits": {"timeout_ms": 250}}, 120000
    ) == pytest.approx(0.25)
    assert ENGINE.subprocess_timeout_seconds({}, 120000) == pytest.approx(120.0)
    assert ENGINE.parse_timeout_ms({"limits": {"timeout_ms": 99}}, 120000) == 100
    assert ENGINE.parse_timeout_ms({"limits": {"timeout_ms": True}}, 120000) == 120000


@pytest.mark.unit
def test_license_failure_takes_precedence_over_benign_config_warning() -> None:
    result = ENGINE.classify_verdi_no_response(
        "*WARN* Cannot open /tmp/novas.conf for read access\n"
        "[ERROR] Could not checkout Verdi license.",
        "",
        1,
    )
    assert result["code"] == "VERDI_LICENSE_UNAVAILABLE"
    assert result["message"] == "Verdi could not check out a license"


@pytest.mark.unit
def test_verdi_action_enforces_100_millisecond_timeout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    observed: dict[str, object] = {}

    class FakeVerdi:
        pid = 31001
        returncode = -9

        def __init__(self, command, **kwargs) -> None:
            observed["command"] = command
            observed["kwargs"] = kwargs
            self.calls = 0

        def communicate(self, timeout=None):
            self.calls += 1
            if self.calls == 1:
                observed["timeout"] = timeout
                raise subprocess.TimeoutExpired(observed["command"], timeout)
            return "", ""

        def wait(self, timeout=None):
            observed["wait_timeout"] = timeout
            return self.returncode

    monkeypatch.setattr(ENGINE.subprocess, "Popen", FakeVerdi)
    monkeypatch.setattr(
        ENGINE.os,
        "killpg",
        lambda pid, signum: observed.setdefault("signals", []).append((pid, signum)),
        raising=False,
    )
    request = {
        "action": "rscheck.inventory",
        "target": {"elab_db": "/tmp/TB.elab++"},
        "args": {"positions": ["top"], "trace_rules": {}},
        "limits": {"timeout_ms": 100},
    }
    ok, error = ENGINE.run_tcl_npi_in_tmpdir(
        request,
        {"target": {}},
        request["target"],
        request["args"],
        "/mock/verdi",
        str(tmp_path),
    )

    assert not ok
    assert error["code"] == "TCL_NPI_TIMEOUT"
    assert observed["timeout"] == pytest.approx(0.1)
    assert observed["kwargs"]["start_new_session"] is True
    assert observed["signals"] == [
        (FakeVerdi.pid, ENGINE.signal.SIGTERM),
        (FakeVerdi.pid, ENGINE.VERDI_KILL_SIGNAL),
    ]
    assert observed["wait_timeout"] == pytest.approx(ENGINE.VERDI_KILL_WAIT_SECONDS)


@pytest.mark.unit
def test_verdi_child_is_reaped_when_engine_receives_sigterm(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    observed: dict[str, object] = {}

    class FakeVerdi:
        pid = 31002
        returncode = -15

        def __init__(self, command, **kwargs) -> None:
            self.calls = 0

        def communicate(self, timeout=None):
            self.calls += 1
            if self.calls == 1:
                raise ENGINE.EngineTermination(ENGINE.signal.SIGTERM)
            observed["reaped"] = True
            return "", ""

        def wait(self, timeout=None):
            observed["wait_timeout"] = timeout
            return self.returncode

    monkeypatch.setattr(ENGINE.subprocess, "Popen", FakeVerdi)
    monkeypatch.setattr(
        ENGINE.os,
        "killpg",
        lambda pid, signum: observed.setdefault("signals", []).append((pid, signum)),
        raising=False,
    )
    request = {
        "action": "rscheck.inventory",
        "target": {"elab_db": "/tmp/TB.elab++"},
        "args": {"positions": ["top"], "trace_rules": {}},
        "limits": {"timeout_ms": 100},
    }

    with pytest.raises(ENGINE.EngineTermination):
        ENGINE.run_tcl_npi_in_tmpdir(
            request,
            {"target": {}},
            request["target"],
            request["args"],
            "/mock/verdi",
            str(tmp_path),
        )

    assert observed["reaped"] is True
    assert observed["signals"] == [
        (FakeVerdi.pid, ENGINE.signal.SIGTERM),
        (FakeVerdi.pid, ENGINE.VERDI_KILL_SIGNAL),
    ]
    assert observed["wait_timeout"] == pytest.approx(ENGINE.VERDI_KILL_WAIT_SECONDS)


@pytest.mark.unit
def test_verdi_cleanup_never_uses_an_unbounded_pipe_drain(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    observed: dict[str, object] = {"timeouts": [], "signals": [], "closed": []}

    class FakePipe:
        def __init__(self, name: str) -> None:
            self.name = name

        def close(self) -> None:
            observed["closed"].append(self.name)

    class FakeVerdi:
        pid = 31003
        returncode = None

        def __init__(self, command, **kwargs) -> None:
            observed["kwargs"] = kwargs
            self.stdin = None
            self.stdout = FakePipe("stdout")
            self.stderr = FakePipe("stderr")

        def communicate(self, timeout=None):
            observed["timeouts"].append(timeout)
            raise subprocess.TimeoutExpired(
                ["verdi"], timeout, output="partial stdout", stderr="partial stderr"
            )

        def wait(self, timeout=None):
            observed["wait_timeout"] = timeout
            raise subprocess.TimeoutExpired(["verdi"], timeout)

    monkeypatch.setattr(ENGINE.subprocess, "Popen", FakeVerdi)
    monkeypatch.setattr(
        ENGINE.os,
        "killpg",
        lambda pid, signum: observed["signals"].append((pid, signum)),
        raising=False,
    )
    request = {
        "action": "rscheck.inventory",
        "target": {"elab_db": "/tmp/TB.elab++"},
        "args": {"positions": ["top"], "trace_rules": {}},
        "limits": {"timeout_ms": 100},
    }

    ok, error = ENGINE.run_tcl_npi_in_tmpdir(
        request,
        {"target": {}},
        request["target"],
        request["args"],
        "/mock/verdi",
        str(tmp_path),
    )

    assert not ok
    assert error["code"] == "TCL_NPI_TIMEOUT"
    assert error["stdout"] == "partial stdout"
    assert error["stderr"] == "partial stderr"
    assert observed["kwargs"]["start_new_session"] is True
    assert observed["timeouts"] == [
        pytest.approx(0.1),
        pytest.approx(ENGINE.VERDI_TERM_WAIT_SECONDS),
        pytest.approx(ENGINE.VERDI_KILL_WAIT_SECONDS),
    ]
    assert observed["signals"] == [
        (FakeVerdi.pid, ENGINE.signal.SIGTERM),
        (FakeVerdi.pid, ENGINE.VERDI_KILL_SIGNAL),
    ]
    assert observed["closed"] == ["stdout", "stderr"]
    assert observed["wait_timeout"] == pytest.approx(ENGINE.VERDI_KILL_WAIT_SECONDS)


@pytest.mark.unit
def test_prepare_rscheck_inventory_writes_stable_inputs(tmp_path: Path) -> None:
    request = {
        "args": {
            "positions": ["top.u_b", "top.u_a"],
            "trace_rules": {"rs_z": "clock_i", "rs_a": "clk"},
            "trace_max_depth": 7,
        }
    }
    env: dict[str, str] = {}
    ok, error = ENGINE.prepare_rscheck_inventory(
        request, {"elab_db": "/tmp/TB.elab++"}, str(tmp_path), env
    )

    assert ok and error is None
    assert Path(env["KDEBUG_RSCHECK_POSITIONS_FILE"]).read_text().splitlines() == [
        "top.u_b",
        "top.u_a",
    ]
    assert Path(env["KDEBUG_RSCHECK_TRACE_RULES_FILE"]).read_text().splitlines() == [
        "rs_a\tclk",
        "rs_z\tclock_i",
    ]
    assert env["KDEBUG_RSCHECK_TRACE_MAX_DEPTH"] == "7"
    assert env["KDEBUG_RSCHECK_CLK_PORT"] == "clk"
    assert env["KDEBUG_RSCHECK_RST_PORT"] == "rst_n"


@pytest.mark.unit
@pytest.mark.parametrize(
    ("request_body", "message"),
    [
        ({"args": {"positions": [], "trace_rules": {}}}, "positions"),
        (
            {"args": {"positions": ["top"], "trace_rules": [], "trace_max_depth": 1}},
            "trace_rules",
        ),
        (
            {"args": {"positions": ["top"], "trace_rules": {}, "trace_max_depth": 0}},
            "trace_max_depth",
        ),
        (
            {"args": {"positions": ["top"], "trace_rules": {}, "trace_max_depth": True}},
            "trace_max_depth",
        ),
        (
            {"args": {"positions": ["top"], "trace_rules": {}, "trace_max_depth": 2.5}},
            "trace_max_depth",
        ),
        (
            {
                "limits": {"timeout_ms": 99},
                "args": {"positions": ["top"], "trace_rules": {}},
            },
            "timeout_ms",
        ),
        (
            {
                "limits": {"timeout_ms": True},
                "args": {"positions": ["top"], "trace_rules": {}},
            },
            "timeout_ms",
        ),
        (
            {
                "limits": {"timeout_ms": "100"},
                "args": {"positions": ["top"], "trace_rules": {}},
            },
            "timeout_ms",
        ),
        (
            {
                "limits": {"timeout_ms": 2147482648},
                "args": {"positions": ["top"], "trace_rules": {}},
            },
            "timeout_ms",
        ),
    ],
)
def test_prepare_rscheck_inventory_rejects_invalid_contract(
    tmp_path: Path, request_body: dict, message: str
) -> None:
    ok, error = ENGINE.prepare_rscheck_inventory(
        request_body, {"elab_db": "/tmp/TB.elab++"}, str(tmp_path), {}
    )
    assert not ok
    assert message in error["message"]


@pytest.mark.unit
def test_partial_elab_marker_adds_one_notice_and_keeps_diagnostics(
    tmp_path: Path,
) -> None:
    (tmp_path / ".hasElabcomError").write_text("")
    data = {
        "inventory": {
            "schema_version": 3,
            "positions": {},
            "warnings": [],
            "notices": [],
        },
        "summary": {"top_count": 1, "top_names": ["top"]},
    }

    ok, result = ENGINE.finalize_rscheck_inventory(
        data, {"elab_db": str(tmp_path)}, "load diagnostic", "", 0
    )
    assert ok
    notices = result["inventory"]["notices"]
    assert len(notices) == 1
    assert "NPI_LOAD_PARTIAL" in notices[0]
    assert "top instance(s) remain queryable" in notices[0]
    assert result["verdi"]["partial_load"] is True
    assert result["verdi"]["stdout_tail"] == "load diagnostic"

    ok, result = ENGINE.finalize_rscheck_inventory(
        result, {"elab_db": str(tmp_path)}, "load diagnostic", "", 0
    )
    assert ok
    assert result["inventory"]["notices"] == notices


@pytest.mark.unit
def test_rscheck_inventory_requires_queryable_top() -> None:
    ok, error = ENGINE.finalize_rscheck_inventory(
        {
            "inventory": {
                "schema_version": 3,
                "positions": {},
                "warnings": [],
                "notices": [],
            },
            "summary": {"top_count": 0, "top_names": []},
        },
        {"elab_db": "/tmp/TB.elab++"},
        "",
        "",
        0,
    )
    assert not ok
    assert error["code"] == "NPI_LOAD"


@pytest.mark.unit
def test_run_tcl_npi_always_removes_temporary_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scratch = tmp_path / "kdebug-tcl-npi-case"

    def make_scratch(prefix: str) -> str:
        assert prefix == "kdebug-tcl-npi-"
        scratch.mkdir()
        (scratch / "leftover").write_text("temporary")
        return str(scratch)

    monkeypatch.setattr(ENGINE, "find_verdi", lambda: "/bin/verdi")
    monkeypatch.setattr(ENGINE.tempfile, "mkdtemp", make_scratch)
    monkeypatch.setattr(
        ENGINE,
        "run_tcl_npi_in_tmpdir",
        lambda request, state, target, args, verdi, tmpdir: (True, {"ok": True}),
    )

    ok, _ = ENGINE.run_tcl_npi(
        {"action": "rscheck.inventory", "target": {"elab_db": "/tmp/TB.elab++"}},
        {"target": {}},
    )
    assert ok
    assert not scratch.exists()


@pytest.mark.unit
def test_run_tcl_npi_signal_removes_temporary_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scratch = tmp_path / "kdebug-tcl-npi-signal"
    observed: dict[str, object] = {}

    def make_scratch(prefix: str) -> str:
        assert prefix == "kdebug-tcl-npi-"
        scratch.mkdir()
        return str(scratch)

    def interrupted(request, state, target, args, verdi, tmpdir):
        (scratch / "leftover").write_text("temporary")
        handler = ENGINE.signal.getsignal(ENGINE.signal.SIGTERM)
        observed["handler"] = handler
        handler(ENGINE.signal.SIGTERM, None)

    monkeypatch.setattr(ENGINE, "find_verdi", lambda: "/bin/verdi")
    monkeypatch.setattr(ENGINE.tempfile, "mkdtemp", make_scratch)
    monkeypatch.setattr(ENGINE, "run_tcl_npi_in_tmpdir", interrupted)

    ok, error = ENGINE.run_tcl_npi(
        {"action": "rscheck.inventory", "target": {"elab_db": "/tmp/TB.elab++"}},
        {"target": {}},
    )

    assert not ok
    assert error["code"] == "TCL_NPI_TERMINATED"
    assert callable(observed["handler"])
    assert not scratch.exists()
