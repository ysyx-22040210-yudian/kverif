from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .runtime import KVerifError, command_text, repository_root, write_json
from .tasks import inspect_module, trace_signal


TUTORIALS = [
    {
        "name": "waveform",
        "input": "bundled Verdi 2018 FSDB",
        "result": "signal changes, X/Z count, and truncation status",
        "requires": "Verdi 2018 and kdebug",
    },
    {
        "name": "module-inspect",
        "input": "bundled parameterized SystemVerilog module",
        "result": "effective parameters, port directions, and instance facts",
        "requires": "VCS/Verdi 2018 and kdebug, or --daidir",
    },
]


def _vcs_executable() -> Optional[str]:
    configured = os.environ.get("VCS")
    if configured:
        path = Path(configured).expanduser()
        if path.exists():
            return str(path.resolve())
    vcs_home = os.environ.get("VCS_HOME")
    if vcs_home:
        candidate = Path(vcs_home).expanduser() / "bin" / "vcs"
        if candidate.exists():
            return str(candidate.resolve())
    return shutil.which("vcs")


def build_module_fixture(build_dir: Path) -> Tuple[Path, List[str]]:
    root = repository_root()
    source = root / "kdebug" / "tests" / "vm" / "npi_actions" / "design.sv"
    vcs = _vcs_executable()
    if not vcs:
        raise KVerifError(
            "VCS_NOT_FOUND",
            "VCS is required to build the module-inspection tutorial database",
            hint="Set VCS_HOME/add vcs to PATH, or pass --daidir for an existing database.",
        )
    if not source.is_file():
        raise KVerifError(
            "TUTORIAL_SOURCE_MISSING",
            "the bundled module tutorial source is missing: %s" % source,
        )
    build_dir.mkdir(parents=True, exist_ok=True)
    argv = [
        vcs,
        "-full64",
        "-sverilog",
        "-kdb",
        "-lca",
        "-debug_access+all",
        "-Xdump_vcsdb",
        str(source),
        "-top",
        "npi_fixture_top",
        "-o",
        str(build_dir / "simv"),
        "-l",
        str(build_dir / "compile.log"),
    ]
    completed = subprocess.run(
        argv,
        cwd=str(build_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    (build_dir / "vcs.stdout.log").write_text(completed.stdout, encoding="utf-8")
    (build_dir / "vcs.stderr.log").write_text(completed.stderr, encoding="utf-8")
    daidir = build_dir / "simv.daidir"
    if completed.returncode != 0 or not daidir.is_dir():
        raise KVerifError(
            "VCS_BUILD_FAILED",
            "VCS did not produce the tutorial simv.daidir",
            hint="Inspect compile.log and vcs.stderr.log in %s." % build_dir,
            details={"command": command_text(argv), "exit_code": completed.returncode},
        )
    return daidir, argv


def run_waveform_tutorial(
    *, output_dir: Path, kdebug_bin: Optional[str] = None, dry_run: bool = False
) -> Dict[str, Any]:
    root = repository_root()
    fixture = root / "examples" / "secondary_development" / "fixtures" / "fsdb_handshake"
    manifest = json.loads((fixture / "signal_manifest.json").read_text(encoding="utf-8"))
    signal = "tb_kverif_handshake.dut.accepted_count"
    expected = next(row for row in manifest["signals"] if row["name"] == signal)
    result = trace_signal(
        fsdb=str(fixture / "waves.fsdb"),
        signal=signal,
        begin=manifest["time_range"]["begin"],
        end=manifest["time_range"]["end"],
        value_format="hex",
        max_rows=100,
        output_dir=output_dir,
        kdebug_bin=kdebug_bin,
        dry_run=dry_run,
    )
    if dry_run:
        result["tutorial"] = {"name": "waveform", "checks": [], "passed": True}
    else:
        checks = [
            {
                "name": "change-count",
                "expected": expected["expected_change_count"],
                "actual": result["summary"]["change_count"],
                "passed": result["summary"]["change_count"] == expected["expected_change_count"],
            },
            {
                "name": "unknown-count",
                "expected": 0,
                "actual": result["summary"]["unknown_count"],
                "passed": result["summary"]["unknown_count"] == 0,
            },
            {
                "name": "complete-window",
                "expected": False,
                "actual": result["summary"]["truncated"],
                "passed": not result["summary"]["truncated"],
            },
        ]
        result["tutorial"] = {
            "name": "waveform",
            "checks": checks,
            "passed": all(row["passed"] for row in checks),
        }
        write_json(Path(result["artifacts"]["result"]), result)
        if not result["tutorial"]["passed"]:
            raise KVerifError(
                "TUTORIAL_ASSERTION_FAILED",
                "the waveform result did not match the bundled manifest",
                details={"checks": checks, "artifacts": result.get("artifacts")},
            )
    write_json(Path(result["artifacts"]["result"]), result)
    return result


def run_module_tutorial(
    *,
    output_dir: Path,
    kdebug_bin: Optional[str] = None,
    daidir: Optional[str] = None,
    no_build: bool = False,
    rebuild: bool = False,
    dry_run: bool = False,
) -> Dict[str, Any]:
    build_command: Optional[List[str]] = None
    if daidir:
        design_db = Path(daidir).expanduser().resolve()
        if not dry_run and not design_db.is_dir():
            raise KVerifError(
                "DAIDIR_NOT_FOUND",
                "module tutorial database was not found: %s" % design_db,
                hint="Pass an existing simv.daidir or omit --daidir to build the fixture.",
            )
    else:
        design_db = output_dir.expanduser().resolve() / "build" / "simv.daidir"
        if dry_run:
            result = inspect_module(
                daidir=str(design_db),
                module="npi_fixture_top.u_alu",
                sections=("parameters", "ports", "instances"),
                max_rows=100,
                output_dir=output_dir,
                kdebug_bin=kdebug_bin,
                dry_run=True,
            )
            result["tutorial"] = {"name": "module-inspect", "checks": [], "passed": True}
            write_json(Path(result["artifacts"]["result"]), result)
            return result
        if rebuild and design_db.exists():
            raise KVerifError(
                "REBUILD_REQUIRES_CLEAN_OUTPUT",
                "the tutorial build directory already exists",
                hint="Choose a new --out directory or remove only its build subdirectory.",
            )
        if not design_db.is_dir():
            if no_build:
                raise KVerifError(
                    "DAIDIR_NOT_FOUND",
                    "the tutorial design database does not exist",
                    hint="Remove --no-build, or pass --daidir for an existing database.",
                )
            design_db, build_command = build_module_fixture(design_db.parent)

    result = inspect_module(
        daidir=str(design_db),
        module="npi_fixture_top.u_alu",
        sections=("parameters", "ports", "instances"),
        max_rows=100,
        output_dir=output_dir,
        kdebug_bin=kdebug_bin,
        dry_run=dry_run,
    )
    if dry_run:
        result["tutorial"] = {"name": "module-inspect", "checks": [], "passed": True}
    else:
        params = {row["name"]: str(row["value"]) for row in result["parameters"]}
        ports = {row["name"]: row["direction"] for row in result["ports"]}
        checks = [
            {"name": "WIDTH", "expected": "12", "actual": params.get("WIDTH"), "passed": params.get("WIDTH") == "12"},
            {"name": "BIAS", "expected": "1", "actual": params.get("BIAS"), "passed": params.get("BIAS") == "1"},
            {
                "name": "port-directions",
                "expected": {"lhs": "input", "rhs": "input", "result": "output"},
                "actual": ports,
                "passed": ports == {"lhs": "input", "rhs": "input", "result": "output"},
            },
        ]
        result["tutorial"] = {
            "name": "module-inspect",
            "checks": checks,
            "passed": all(row["passed"] for row in checks),
            "design_db": str(design_db),
            "build_command": command_text(build_command) if build_command else None,
        }
        write_json(Path(result["artifacts"]["result"]), result)
        if not result["tutorial"]["passed"]:
            raise KVerifError(
                "TUTORIAL_ASSERTION_FAILED",
                "the module result did not match the bundled design",
                details={"checks": checks, "artifacts": result.get("artifacts")},
            )
    write_json(Path(result["artifacts"]["result"]), result)
    return result


def run_all_tutorials(
    *,
    output_dir: Path,
    kdebug_bin: Optional[str] = None,
    daidir: Optional[str] = None,
    no_build: bool = False,
    rebuild: bool = False,
    dry_run: bool = False,
) -> Dict[str, Any]:
    output_dir = output_dir.expanduser().resolve()
    waveform = run_waveform_tutorial(
        output_dir=output_dir / "waveform", kdebug_bin=kdebug_bin, dry_run=dry_run
    )
    module = run_module_tutorial(
        output_dir=output_dir / "module-inspect",
        kdebug_bin=kdebug_bin,
        daidir=daidir,
        no_build=no_build,
        rebuild=rebuild,
        dry_run=dry_run,
    )
    report = {
        "schema": "kverif.tutorial-suite.v1",
        "ok": bool(waveform["tutorial"]["passed"] and module["tutorial"]["passed"]),
        "summary": {"tutorials": 2, "passed": 2},
        "tutorials": [
            {"name": "waveform", "result": waveform["artifacts"]["result"]},
            {"name": "module-inspect", "result": module["artifacts"]["result"]},
        ],
    }
    write_json(output_dir / "result.json", report)
    return report
