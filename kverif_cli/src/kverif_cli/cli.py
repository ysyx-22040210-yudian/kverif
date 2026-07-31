from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import __version__
from .doctor import human_doctor, run_doctor
from .runtime import KVerifError
from .scaffold import create_signal_check
from .tasks import (
    DEFAULT_MODULE_SECTIONS,
    artifact_lines,
    human_inspect_module,
    human_trace_signal,
    inspect_module,
    trace_signal,
)
from .tutorials import (
    TUTORIALS,
    run_all_tutorials,
    run_module_tutorial,
    run_waveform_tutorial,
)


TASKS = [
    {
        "name": "inspect-module",
        "purpose": "show effective parameters, ports, connections, and child instances",
        "input": "simv.daidir",
    },
    {
        "name": "trace-signal",
        "purpose": "show signal activity, X/Z count, and waveform changes",
        "input": "waves.fsdb",
    },
    {
        "name": "tutorial",
        "purpose": "run checked examples using bundled RTL and real FSDB data",
        "input": "bundled fixtures",
    },
    {
        "name": "new signal-check",
        "purpose": "create a CLI-only Bash/csh/Perl/Python starter project",
        "input": "language choice",
    },
]


def _add_output_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", help="emit one machine-readable JSON object")


def _add_task_flags(parser: argparse.ArgumentParser, default_out: str) -> None:
    _add_output_flags(parser)
    parser.add_argument("--out", default=default_out, help="artifact directory")
    parser.add_argument("--kdebug-bin", help="explicit kdebug executable path")
    parser.add_argument("--show-command", action="store_true", help="print the generated low-level command")
    parser.add_argument("--dry-run", action="store_true", help="write replay artifacts without running kdebug")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kverif",
        description="Beginner-friendly task commands over the stable KVerif executables",
    )
    parser.add_argument("--version", action="version", version="kverif %s" % __version__)
    sub = parser.add_subparsers(dest="command", required=True)

    child = sub.add_parser("tasks", help="list beginner-facing task commands")
    _add_output_flags(child)

    child = sub.add_parser("doctor", help="check the local EDA and KVerif environment")
    _add_output_flags(child)
    child.add_argument("--kdebug-bin")
    child.add_argument("--fsdb", help="also validate a project FSDB path")
    child.add_argument("--daidir", help="also validate a project simv.daidir path")
    child.add_argument("--require-vcs", action="store_true", help="treat missing VCS as a failure")
    child.add_argument("--skip-probe", action="store_true", help="skip the kdebug actions smoke probe")

    child = sub.add_parser("inspect-module", help="inspect one elaborated module instance")
    _add_task_flags(child, "kverif-results/inspect-module")
    child.add_argument("--input", "--daidir", dest="daidir", required=True, help="simv.daidir path")
    child.add_argument("--module", required=True, help="full elaborated instance path")
    child.add_argument(
        "--sections",
        default=",".join(DEFAULT_MODULE_SECTIONS),
        help="comma-separated module sections (default: parameters,ports,instances)",
    )
    child.add_argument("--max-rows", type=int, default=200)

    child = sub.add_parser("trace-signal", help="inspect activity for one real FSDB signal")
    _add_task_flags(child, "kverif-results/trace-signal")
    child.add_argument("--input", "--fsdb", dest="fsdb", required=True, help="FSDB path")
    child.add_argument("--signal", required=True, help="full FSDB signal name")
    child.add_argument("--begin", required=True, help="window start, for example 0ns")
    child.add_argument("--end", required=True, help="window end, for example 100ns")
    child.add_argument("--format", choices=["bin", "oct", "dec", "hex"], default="hex")
    child.add_argument("--max-rows", type=int, default=200)

    child = sub.add_parser("tutorial", help="run a checked tutorial using bundled inputs")
    _add_task_flags(child, "kverif-results/tutorial")
    child.add_argument("name", choices=["list", "waveform", "module-inspect", "all"])
    child.add_argument("--daidir", help="reuse an existing module-tutorial simv.daidir")
    child.add_argument("--no-build", action="store_true", help="do not auto-build a missing module database")
    child.add_argument("--rebuild", action="store_true", help="require a fresh module tutorial build directory")

    child = sub.add_parser("new", help="create an executable-only secondary-development starter")
    _add_output_flags(child)
    child.add_argument("kind", choices=["signal-check"])
    child.add_argument("--lang", choices=["sh", "csh", "perl", "python"], required=True)
    child.add_argument("--out", required=True)
    child.add_argument("--force", action="store_true")
    return parser


def _json_print(payload: Dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _human_tasks() -> str:
    lines = ["KVerif beginner tasks", ""]
    for row in TASKS:
        lines.append("  %-20s %s" % (row["name"], row["purpose"]))
        lines.append("  %-20s input: %s" % ("", row["input"]))
    lines.extend(["", "Start with: kverif doctor", "Then run:  kverif tutorial waveform"])
    return "\n".join(lines)


def _human_tutorial_list() -> str:
    lines = ["Available KVerif tutorials", ""]
    for row in TUTORIALS:
        lines.append("  %s" % row["name"])
        lines.append("    input:    %s" % row["input"])
        lines.append("    result:   %s" % row["result"])
        lines.append("    requires: %s" % row["requires"])
    lines.extend(["", "Run one with: kverif tutorial waveform"])
    return "\n".join(lines)


def _show_task_result(result: Dict[str, Any], body: str, show_command: bool) -> None:
    print(body)
    print(artifact_lines(result))
    if show_command:
        print("\nUnderlying command:\n  %s" % result.get("underlying_command"))


def run(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "tasks":
            payload = {"schema": "kverif.tasks.v1", "ok": True, "tasks": TASKS}
            _json_print(payload) if args.json else print(_human_tasks())
            return 0

        if args.command == "doctor":
            report = run_doctor(
                kdebug_bin=args.kdebug_bin,
                fsdb=args.fsdb,
                daidir=args.daidir,
                require_vcs=args.require_vcs,
                skip_probe=args.skip_probe,
            )
            _json_print(report) if args.json else print(human_doctor(report))
            return 0 if report["ok"] else 1

        if args.command == "inspect-module":
            result = inspect_module(
                daidir=args.daidir,
                module=args.module,
                sections=args.sections.split(","),
                max_rows=args.max_rows,
                output_dir=Path(args.out),
                kdebug_bin=args.kdebug_bin,
                dry_run=args.dry_run,
            )
            if args.json:
                _json_print(result)
            else:
                _show_task_result(result, human_inspect_module(result), args.show_command)
            return 0

        if args.command == "trace-signal":
            result = trace_signal(
                fsdb=args.fsdb,
                signal=args.signal,
                begin=args.begin,
                end=args.end,
                value_format=args.format,
                max_rows=args.max_rows,
                output_dir=Path(args.out),
                kdebug_bin=args.kdebug_bin,
                dry_run=args.dry_run,
            )
            if args.json:
                _json_print(result)
            else:
                _show_task_result(result, human_trace_signal(result), args.show_command)
            return 0

        if args.command == "tutorial":
            if args.name == "list":
                payload = {"schema": "kverif.tutorials.v1", "ok": True, "tutorials": TUTORIALS}
                _json_print(payload) if args.json else print(_human_tutorial_list())
                return 0
            output_dir = Path(args.out) / args.name if args.name != "all" else Path(args.out)
            if args.name == "waveform":
                if not args.json and not args.dry_run:
                    print("[1/2] Querying the bundled real FSDB...")
                result = run_waveform_tutorial(
                    output_dir=output_dir,
                    kdebug_bin=args.kdebug_bin,
                    dry_run=args.dry_run,
                )
                body = human_trace_signal(result)
                if not args.dry_run:
                    body += "\nTutorial checks: PASS"
            elif args.name == "module-inspect":
                if not args.json and not args.dry_run:
                    if args.daidir:
                        print("[1/2] Opening the supplied design database...")
                    else:
                        print("[1/2] Building the tiny VCS tutorial database...")
                result = run_module_tutorial(
                    output_dir=output_dir,
                    kdebug_bin=args.kdebug_bin,
                    daidir=args.daidir,
                    no_build=args.no_build,
                    rebuild=args.rebuild,
                    dry_run=args.dry_run,
                )
                body = human_inspect_module(result)
                if not args.dry_run:
                    body += "\nTutorial checks: PASS"
            else:
                result = run_all_tutorials(
                    output_dir=output_dir,
                    kdebug_bin=args.kdebug_bin,
                    daidir=args.daidir,
                    no_build=args.no_build,
                    rebuild=args.rebuild,
                    dry_run=args.dry_run,
                )
                body = "PASS  all tutorials completed\n\nResult: %s" % (output_dir.resolve() / "result.json")
            if args.json:
                _json_print(result)
            else:
                if args.name == "all":
                    print(body)
                else:
                    _show_task_result(result, body, args.show_command)
            return 0

        if args.command == "new":
            result = create_signal_check(
                language=args.lang, output_dir=Path(args.out), force=args.force
            )
            if args.json:
                _json_print(result)
            else:
                print("PASS  starter project created")
                print("\nDirectory: %s" % result["summary"]["output_dir"])
                print("Run:       KVERIF_HOME=/opt/kverif bash %s/example.sh" % result["summary"]["output_dir"])
            return 0
    except KVerifError as exc:
        if getattr(args, "json", False):
            _json_print(exc.payload())
        else:
            print("ERROR [%s] %s" % (exc.code, exc.message), file=sys.stderr)
            if exc.hint:
                print("Next: %s" % exc.hint, file=sys.stderr)
            if exc.details.get("artifacts"):
                print("Artifacts: %s" % exc.details["artifacts"], file=sys.stderr)
        return exc.exit_code
    parser.error("unhandled command")
    return 2


def main() -> None:
    raise SystemExit(run())
