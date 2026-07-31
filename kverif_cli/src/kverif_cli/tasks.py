from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .runtime import (
    Json,
    KVerifError,
    direction_label,
    find_tool,
    persist_task_failure,
    persist_task_result,
    run_json_command,
)


DEFAULT_MODULE_SECTIONS = ("parameters", "ports", "instances")
MODULE_SECTIONS = {
    "continuous_assignments",
    "functions",
    "generate_scopes",
    "instances",
    "instances_in_generate",
    "io",
    "language_interfaces",
    "nets",
    "parameters",
    "ports",
    "primitives",
    "always_processes",
    "initial_processes",
    "tasks",
    "variables",
}


def _object(row: Any) -> Json:
    if not isinstance(row, dict):
        return {}
    value = row.get("object", row)
    return value if isinstance(value, dict) else {}


def _rows(value: Any) -> List[Json]:
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


def _parameter_value(row: Json) -> Any:
    values = row.get("values")
    if isinstance(values, dict):
        for key in ("dec", "int", "hex", "bin", "string", "real"):
            if values.get(key) not in (None, ""):
                return values[key]
    for key in ("value", "decompiled"):
        if row.get(key) not in (None, ""):
            return row[key]
    return None


def inspect_module(
    *,
    daidir: str,
    module: str,
    sections: Iterable[str] = DEFAULT_MODULE_SECTIONS,
    max_rows: int = 200,
    output_dir: Path,
    kdebug_bin: Optional[str] = None,
    dry_run: bool = False,
) -> Json:
    selected = [item.strip() for item in sections if item.strip()]
    unknown_sections = sorted(set(selected) - MODULE_SECTIONS)
    if unknown_sections:
        raise KVerifError(
            "INVALID_MODULE_SECTION",
            "unknown module section(s): %s" % ", ".join(unknown_sections),
            hint="Run 'kverif inspect-module --help' and use a documented section name.",
        )
    if max_rows < 1:
        raise KVerifError("INVALID_LIMIT", "--max-rows must be greater than zero")
    design_db = Path(daidir).expanduser()
    if not dry_run and not design_db.is_dir():
        raise KVerifError(
            "DAIDIR_NOT_FOUND",
            "design database directory was not found: %s" % design_db,
            hint="Pass the full path to the VCS simv.daidir directory.",
        )
    argv = [
        find_tool("kdebug", kdebug_bin),
        "--json",
        "action",
        "module.inspect",
        "--daidir",
        str(design_db),
        "--arg",
        "module=%s" % module,
        "--arg",
        "sections=%s" % json.dumps(selected, separators=(",", ":")),
        "--limit",
        "max_rows=%d" % max_rows,
    ]
    if dry_run:
        result: Json = {
            "schema": "kverif.task-result.v1",
            "command": "inspect-module",
            "ok": True,
            "dry_run": True,
            "summary": {"module": module, "sections": selected},
            "parameters": [],
            "ports": [],
            "instances": [],
        }
        return persist_task_result(
            result, output_dir=output_dir, argv=argv, tool_response=None
        )

    try:
        response, _ = run_json_command(argv)
    except KVerifError as exc:
        persist_task_failure(exc, output_dir=output_dir, argv=argv)
        raise
    data = response.get("data") if isinstance(response.get("data"), dict) else {}
    section_data = data.get("sections") if isinstance(data.get("sections"), dict) else {}
    parameters = []
    for row in _rows(section_data.get("parameters")):
        obj = _object(row)
        parameters.append(
            {
                "name": obj.get("name"),
                "value": _parameter_value(row),
                "width": obj.get("size"),
                "local": bool(obj.get("local_param")),
                "source": obj.get("file"),
                "line": obj.get("line"),
            }
        )

    ports = []
    for row in _rows(section_data.get("ports")):
        obj = _object(row)
        connections = row.get("connections") if isinstance(row.get("connections"), dict) else {}
        high = connections.get("high") if isinstance(connections.get("high"), dict) else {}
        low = connections.get("low") if isinstance(connections.get("low"), dict) else {}
        ports.append(
            {
                "name": obj.get("name"),
                "direction": direction_label(obj.get("direction")),
                "width": obj.get("size"),
                "full_name": obj.get("full_name"),
                "high_connection": high.get("full_name"),
                "low_connection": low.get("full_name"),
            }
        )

    instances = []
    for row in _rows(section_data.get("instances")):
        obj = _object(row)
        instances.append(
            {
                "name": obj.get("name"),
                "full_name": obj.get("full_name"),
                "definition": obj.get("def_name"),
                "source": obj.get("file") or obj.get("def_file"),
                "line": obj.get("line") or obj.get("def_line"),
            }
        )

    module_row = data.get("module_object") if isinstance(data.get("module_object"), dict) else {}
    module_object = _object(module_row)
    response_summary = response.get("summary") if isinstance(response.get("summary"), dict) else {}
    result = {
        "schema": "kverif.task-result.v1",
        "command": "inspect-module",
        "ok": True,
        "dry_run": False,
        "summary": {
            "module": data.get("module") or response_summary.get("module") or module,
            "definition": module_object.get("def_name"),
            "parameter_count": len(parameters),
            "port_count": len(ports),
            "instance_count": len(instances),
            "truncated": bool(response_summary.get("truncated")),
        },
        "parameters": parameters,
        "ports": ports,
        "instances": instances,
    }
    return persist_task_result(
        result, output_dir=output_dir, argv=argv, tool_response=response
    )


def trace_signal(
    *,
    fsdb: str,
    signal: str,
    begin: str,
    end: str,
    value_format: str = "hex",
    max_rows: int = 200,
    output_dir: Path,
    kdebug_bin: Optional[str] = None,
    dry_run: bool = False,
) -> Json:
    if max_rows < 1:
        raise KVerifError("INVALID_LIMIT", "--max-rows must be greater than zero")
    waveform = Path(fsdb).expanduser()
    if not dry_run and not waveform.is_file():
        raise KVerifError(
            "FSDB_NOT_FOUND",
            "waveform file was not found: %s" % waveform,
            hint="Pass the full path to a readable FSDB file.",
        )
    argv = [
        find_tool("kdebug", kdebug_bin),
        "--json",
        "action",
        "signal.scan",
        "--fsdb",
        str(waveform),
        "--arg",
        "signal=%s" % signal,
        "--arg",
        "begin=%s" % begin,
        "--arg",
        "end=%s" % end,
        "--arg",
        "format=%s" % value_format,
        "--limit",
        "max_rows=%d" % max_rows,
    ]
    if dry_run:
        result: Json = {
            "schema": "kverif.task-result.v1",
            "command": "trace-signal",
            "ok": True,
            "dry_run": True,
            "summary": {
                "signal": signal,
                "begin": begin,
                "end": end,
                "format": value_format,
            },
            "changes": [],
        }
        return persist_task_result(
            result, output_dir=output_dir, argv=argv, tool_response=None
        )

    try:
        response, _ = run_json_command(argv)
    except KVerifError as exc:
        persist_task_failure(exc, output_dir=output_dir, argv=argv)
        raise
    response_summary = response.get("summary") if isinstance(response.get("summary"), dict) else {}
    data = response.get("data") if isinstance(response.get("data"), dict) else {}
    changes = _rows(data.get("changes"))
    result = {
        "schema": "kverif.task-result.v1",
        "command": "trace-signal",
        "ok": True,
        "dry_run": False,
        "summary": {
            "signal": signal,
            "begin": begin,
            "end": end,
            "format": value_format,
            "change_count": response_summary.get("change_count", len(changes)),
            "unknown_count": response_summary.get("unknown_count", 0),
            "returned_count": len(changes),
            "truncated": bool(response_summary.get("truncated")),
        },
        "changes": changes,
    }
    return persist_task_result(
        result, output_dir=output_dir, argv=argv, tool_response=response
    )


def human_inspect_module(result: Json) -> str:
    summary = result.get("summary", {})
    if result.get("dry_run"):
        return "DRY RUN  module query prepared\nModule: %s" % summary.get("module")
    lines = [
        "PASS  module inspection completed",
        "",
        "Module path: %s" % summary.get("module"),
        "Definition: %s" % (summary.get("definition") or "not reported"),
        "Parameters: %s" % summary.get("parameter_count", 0),
    ]
    for row in result.get("parameters", []):
        suffix = " (localparam)" if row.get("local") else ""
        lines.append("  - %s = %s%s" % (row.get("name"), row.get("value"), suffix))
    lines.append("Ports: %s" % summary.get("port_count", 0))
    for row in result.get("ports", []):
        width = row.get("width")
        width_text = "[%s bits]" % width if width not in (None, 1) else ""
        lines.append(
            "  - %-6s %-20s %s" % (row.get("direction"), row.get("name"), width_text)
        )
    lines.append("Child instances: %s" % summary.get("instance_count", 0))
    for row in result.get("instances", []):
        lines.append("  - %s (%s)" % (row.get("full_name"), row.get("definition") or "unknown"))
    return "\n".join(lines)


def human_trace_signal(result: Json) -> str:
    summary = result.get("summary", {})
    if result.get("dry_run"):
        return "DRY RUN  waveform query prepared\nSignal: %s" % summary.get("signal")
    return "\n".join(
        [
            "PASS  waveform inspection completed",
            "",
            "Signal: %s" % summary.get("signal"),
            "Window: %s .. %s" % (summary.get("begin"), summary.get("end")),
            "Changes: %s" % summary.get("change_count"),
            "Unknown values: %s" % summary.get("unknown_count"),
            "Truncated: %s" % ("yes" if summary.get("truncated") else "no"),
        ]
    )


def artifact_lines(result: Json) -> str:
    artifacts = result.get("artifacts", {})
    lines = ["", "Artifacts:"]
    for label in ("result", "tool_response", "replay"):
        if artifacts.get(label):
            lines.append("  %-13s %s" % (label + ":", artifacts[label]))
    return "\n".join(lines)
