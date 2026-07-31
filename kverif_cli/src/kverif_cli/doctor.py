from __future__ import annotations

import getpass
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .runtime import KVerifError, find_tool, repository_root, run_json_command


Check = Dict[str, Any]


def _check(
    name: str,
    status: str,
    message: str,
    *,
    required: bool = False,
    hint: str = "",
) -> Check:
    return {
        "name": name,
        "status": status,
        "required": required,
        "message": message,
        "hint": hint,
    }


def _executable_from_home(home: Optional[str], name: str) -> Optional[Path]:
    if not home:
        return None
    base = Path(home).expanduser()
    for candidate in (base / "bin" / name, base / "bin" / (name + ".exe")):
        if candidate.exists():
            return candidate.resolve()
    return None


def _find_eda_executable(home_env: str, name: str) -> Tuple[Optional[Path], Optional[Path]]:
    home_value = os.environ.get(home_env)
    executable = _executable_from_home(home_value, name)
    if executable:
        return executable, Path(home_value).expanduser().resolve()
    located = shutil.which(name)
    if not located:
        return None, Path(home_value).expanduser().resolve() if home_value else None
    executable = Path(located).resolve()
    return executable, executable.parent.parent


def _fixture_check(root: Path) -> Check:
    fixture = root / "examples" / "secondary_development" / "fixtures" / "fsdb_handshake"
    fsdb = fixture / "waves.fsdb"
    manifest_path = fixture / "signal_manifest.json"
    if not fsdb.is_file() or not manifest_path.is_file():
        return _check(
            "tutorial-fixture",
            "FAIL",
            "the bundled FSDB tutorial fixture is incomplete",
            required=True,
            hint="Restore examples/secondary_development/fixtures/fsdb_handshake.",
        )
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected = manifest["artifact"]["sha256"]
        actual = hashlib.sha256(fsdb.read_bytes()).hexdigest()
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        return _check(
            "tutorial-fixture",
            "FAIL",
            "the bundled fixture metadata could not be read: %s" % exc,
            required=True,
        )
    if expected != actual:
        return _check(
            "tutorial-fixture",
            "FAIL",
            "the bundled FSDB checksum does not match its manifest",
            required=True,
            hint="Restore the fixture before running tutorials.",
        )
    return _check(
        "tutorial-fixture",
        "PASS",
        "real Verdi 2018 FSDB fixture is present and its checksum matches",
        required=True,
    )


def run_doctor(
    *,
    kdebug_bin: Optional[str] = None,
    fsdb: Optional[str] = None,
    daidir: Optional[str] = None,
    require_vcs: bool = False,
    skip_probe: bool = False,
) -> Dict[str, Any]:
    root = repository_root()
    checks: List[Check] = []

    username = getpass.getuser()
    if username == "root":
        checks.append(
            _check(
                "user",
                "WARN",
                "running as root; production EDA checks should use the ordinary verification user",
                hint="On the standard VM, run the command as host.",
            )
        )
    else:
        checks.append(_check("user", "PASS", "running as ordinary user %s" % username))

    version = sys.version_info
    if version >= (3, 8):
        checks.append(
            _check(
                "python",
                "PASS",
                "Python %d.%d.%d is supported" % version[:3],
                required=True,
            )
        )
    else:
        checks.append(
            _check(
                "python",
                "FAIL",
                "Python 3.8 or newer is required; found %d.%d.%d" % version[:3],
                required=True,
            )
        )

    resolved_kdebug: Optional[str] = None
    try:
        resolved_kdebug = find_tool("kdebug", kdebug_bin)
        checks.append(
            _check("kdebug", "PASS", "kdebug executable: %s" % resolved_kdebug, required=True)
        )
    except KVerifError as exc:
        checks.append(_check("kdebug", "FAIL", exc.message, required=True, hint=exc.hint))

    verdi, verdi_home = _find_eda_executable("VERDI_HOME", "verdi")
    if verdi:
        checks.append(_check("verdi", "PASS", "Verdi executable: %s" % verdi, required=True))
    else:
        checks.append(
            _check(
                "verdi",
                "FAIL",
                "Verdi was not found",
                required=True,
                hint="Set VERDI_HOME or add verdi to PATH.",
            )
        )

    npi_tcl = verdi_home / "share" / "NPI" / "L1" / "TCL" / "npi_L1.tcl" if verdi_home else None
    if npi_tcl and npi_tcl.is_file():
        checks.append(
            _check("npi-tcl", "PASS", "Verdi Tcl NPI entry: %s" % npi_tcl, required=True)
        )
    else:
        checks.append(
            _check(
                "npi-tcl",
                "FAIL",
                "Verdi Tcl NPI entry was not found under the detected installation",
                required=True,
                hint="Use a Verdi installation that provides share/NPI/L1/TCL/npi_L1.tcl.",
            )
        )

    vcs, _ = _find_eda_executable("VCS_HOME", "vcs")
    if vcs:
        checks.append(_check("vcs", "PASS", "VCS executable: %s" % vcs, required=require_vcs))
    else:
        checks.append(
            _check(
                "vcs",
                "FAIL" if require_vcs else "WARN",
                "VCS was not found; prebuilt FSDB queries still work, but module tutorial builds do not",
                required=require_vcs,
                hint="Set VCS_HOME or add vcs to PATH before building a design database.",
            )
        )

    checks.append(_fixture_check(root))

    for name, value, kind in (("input-fsdb", fsdb, "file"), ("input-daidir", daidir, "directory")):
        if not value:
            continue
        path = Path(value).expanduser()
        exists = path.is_file() if kind == "file" else path.is_dir()
        checks.append(
            _check(
                name,
                "PASS" if exists else "FAIL",
                "%s: %s" % (kind, path),
                required=True,
                hint="Check the absolute input path and permissions." if not exists else "",
            )
        )

    if resolved_kdebug and not skip_probe:
        try:
            response, _ = run_json_command([resolved_kdebug, "--json", "actions"])
            action_count = len(response.get("data", {}).get("actions", []))
            if not action_count:
                action_count = len(response.get("actions", []))
            checks.append(
                _check(
                    "kdebug-probe",
                    "PASS",
                    "kdebug JSON action catalog responded%s"
                    % (" with %d actions" % action_count if action_count else ""),
                    required=True,
                )
            )
        except KVerifError as exc:
            checks.append(
                _check(
                    "kdebug-probe",
                    "FAIL",
                    exc.message,
                    required=True,
                    hint=exc.hint,
                )
            )
    elif skip_probe:
        checks.append(_check("kdebug-probe", "SKIP", "command probe skipped by request"))

    required_failures = [row for row in checks if row["required"] and row["status"] == "FAIL"]
    warnings = [row for row in checks if row["status"] == "WARN"]
    return {
        "schema": "kverif.doctor.v1",
        "ok": not required_failures,
        "summary": {
            "status": "PASS" if not required_failures else "FAIL",
            "checks": len(checks),
            "required_failures": len(required_failures),
            "warnings": len(warnings),
            "kverif_home": str(root),
        },
        "checks": checks,
    }


def human_doctor(report: Dict[str, Any]) -> str:
    lines = ["KVerif environment check", ""]
    for row in report["checks"]:
        lines.append("[%-4s] %-18s %s" % (row["status"], row["name"], row["message"]))
        if row.get("hint") and row["status"] in {"FAIL", "WARN"}:
            lines.append("       Next: %s" % row["hint"])
    lines.extend(
        [
            "",
            "%s  %d checks, %d required failures, %d warnings"
            % (
                report["summary"]["status"],
                report["summary"]["checks"],
                report["summary"]["required_failures"],
                report["summary"]["warnings"],
            ),
        ]
    )
    return "\n".join(lines)
