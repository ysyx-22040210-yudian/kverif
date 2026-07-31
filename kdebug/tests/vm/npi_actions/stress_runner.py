#!/usr/bin/env python3
"""Repeat every public Tcl NPI action and verify stable semantic results."""

from __future__ import print_function

import argparse
import concurrent.futures
import csv
import datetime
import hashlib
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import time


MODULE_KINDS = (
    ("continuous_assignments", "npi_fixture_top.u_alu", 1),
    ("functions", "npi_fixture_top.u_alu", 1),
    ("generate_scopes", "npi_fixture_top", 1),
    ("instances", "npi_fixture_top", 1),
    ("instances_in_generate", "npi_fixture_top", 1),
    ("io", "npi_fixture_top.u_alu", 3),
    ("language_interfaces", "npi_fixture_top", 0),
    ("nets", "npi_fixture_top", 3),
    ("parameters", "npi_fixture_top.u_alu", 3),
    ("ports", "npi_fixture_top.u_alu", 3),
    ("primitives", "npi_fixture_top", 1),
    ("always_processes", "npi_fixture_top.u_alu", 1),
    ("initial_processes", "npi_fixture_top", 1),
    ("tasks", "npi_fixture_top", 1),
    ("variables", "npi_fixture_top.u_alu", 1),
)

EXPECTED_DOMAINS = {
    "language", "module_library", "netlist", "text", "design_manipulation",
    "fsdb_reader", "transaction_writer", "fsdb_writer", "coverage", "vcs",
    "power", "crdb",
}


def utc_now():
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def ensure(condition, message):
    if not condition:
        raise AssertionError(message)


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def percentile(values, percent):
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * percent
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def slug(value):
    return value.replace("/", "_").replace("\\", "_").replace(" ", "_")


def object_rows(data, key="items"):
    rows = []
    for row in data.get(key, []) or []:
        if isinstance(row, dict):
            rows.append(row.get("object", row))
    return rows


def row_by_name(items, name):
    for row in items:
        obj = row.get("object", row) if isinstance(row, dict) else {}
        if obj.get("name") == name:
            return row
    return None


def nonempty_files(path):
    if not os.path.isdir(path):
        return []
    found = []
    for root, _dirs, files in os.walk(path):
        for name in files:
            candidate = os.path.join(root, name)
            if os.path.getsize(candidate) > 0:
                found.append(candidate)
    return found


def make_cases():
    cases = [
        {"id": "npi.capabilities", "action": "npi.capabilities"},
        {"id": "language.resolve", "action": "language.resolve", "design": True,
         "args": ["name=npi_fixture_top.u_alu"]},
        {"id": "language.iterate", "action": "language.iterate", "design": True,
         "args": ["name=npi_fixture_top.u_alu", "object_type=npiParameter"], "limit": True},
        {"id": "language.relate", "action": "language.relate", "design": True,
         "args": ["name=npi_fixture_top.u_alu.result", "relation_type=npiHighConn"]},
        {"id": "language.value", "action": "language.value", "design": True,
         "args": ["name=npi_fixture_top.u_alu.WIDTH", "format=npiDecStrVal"]},
        {"id": "module.find_instances", "action": "module.find_instances", "design": True,
         "args": ["definition=npi_fixture_alu"], "limit": True},
        {"id": "module.inspect", "action": "module.inspect", "design": True,
         "args": ["module=npi_fixture_top.u_alu",
                  "sections=[\"parameters\",\"ports\",\"io\",\"nets\",\"variables\",\"functions\",\"continuous_assignments\",\"always_processes\"]"],
         "limit": True},
    ]
    for kind, module, minimum in MODULE_KINDS:
        cases.append({
            "id": "module.objects." + kind,
            "action": "module.objects",
            "kind": kind,
            "minimum": minimum,
            "design": True,
            "args": ["module=" + module, "kind=" + kind],
            "limit": True,
        })
    cases.extend([
        {"id": "netlist.resolve", "action": "netlist.resolve", "design": True,
         "args": ["name=npi_fixture_top.result", "object_type=npiNlNet"]},
        {"id": "netlist.iterate", "action": "netlist.iterate", "design": True,
         "args": ["name=npi_fixture_top", "object_type=npiNlNet"], "limit": True},
        {"id": "text.line", "action": "text.line", "design": True, "dynamic": "text.line"},
        {"id": "text.words", "action": "text.words", "design": True, "dynamic": "text.words", "limit": True},
        {"id": "text.replace_line", "action": "text.replace_line", "design": True,
         "dynamic": "text.replace_line"},
        {"id": "dm.add_net", "action": "dm.add_net", "design": True, "dynamic": "dm.add_net"},
        {"id": "dm.clone_module", "action": "dm.clone_module", "design": True,
         "dynamic": "dm.clone_module"},
        {"id": "vcs.summary", "action": "vcs.summary", "design": True},
        {"id": "power.resolve", "action": "power.resolve", "dynamic": "power.resolve",
         "license_allowed": True},
        {"id": "power.list", "action": "power.list", "dynamic": "power.list",
         "license_allowed": True, "limit": True},
        {"id": "crdb.resolve", "action": "crdb.resolve",
         "args": ["name=npi_crdb_top.state", "level=RTL"], "dynamic": "crdb"},
        {"id": "crdb.correlates", "action": "crdb.correlates",
         "args": ["name=npi_crdb_top.state", "level=RTL"], "dynamic": "crdb", "limit": True},
        {"id": "transaction.writer.create", "action": "transaction.writer.create",
         "dynamic": "transaction.writer.create"},
        {"id": "fsdb.writer.create_scope", "action": "fsdb.writer.create_scope",
         "dynamic": "fsdb.writer.create_scope"},
    ])
    return cases


def prepare_power_copy(context, case_id, iteration):
    destination = os.path.join(context["output"], "generated", slug(case_id), "%04d-power" % iteration)
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    shutil.copytree(os.path.join(context["fixture"], "power"), destination)
    return destination


def build_command(case, iteration, context):
    command = [context["kdebug"], "--json", "action", case["action"]]
    if case.get("design"):
        command.extend(["--daidir", os.path.join(context["fixture"], "design", "simv.daidir")])

    arguments = list(case.get("args", []))
    dynamic = case.get("dynamic")
    generated = os.path.join(context["output"], "generated", slug(case["id"]), "%04d" % iteration)

    if dynamic in ("text.line", "text.words"):
        arguments.extend(["file=" + context["source"], "line=27"])
    elif dynamic == "text.replace_line":
        output = os.path.join(generated, "design.patched.sv")
        arguments.extend(["file=" + context["source"], "line=27",
                          "content=    sum = lhs - rhs;", "output=" + output])
    elif dynamic == "dm.add_net":
        arguments.extend(["module=npi_fixture_top", "name=debug_bus_%04d" % iteration,
                          "net_type=npiDmNetWire", "packed_left=7", "packed_right=0",
                          "output_dir=" + os.path.join(generated, "dm-add-net")])
    elif dynamic == "dm.clone_module":
        arguments.extend(["module=npi_fixture_alu", "new_name=npi_fixture_alu_clone_%04d" % iteration,
                          "output_dir=" + os.path.join(generated, "dm-clone")])
    elif dynamic in ("power.resolve", "power.list"):
        power_dir = prepare_power_copy(context, case["id"], iteration)
        command.extend(["--target", "filelist=" + os.path.join(power_dir, "run.f")])
        command.extend(["--target", "upf=" + os.path.join(power_dir, "demo.upf")])
        command.extend(["--target", "workdir=" + power_dir])
        command.extend(["--target", "defines=[\"NOVAS_UPF_PKG\"]"])
        arguments.append("name=system/PD_TOP")
        arguments.append("object_type=" + ("npiPwPowerDomain" if dynamic == "power.resolve" else "npiPwElement"))
    elif dynamic == "crdb":
        arguments.insert(0, "crdb=" + os.path.join(context["fixture"], "crdb", "dut.crdb"))
    elif dynamic == "transaction.writer.create":
        arguments.extend([
            "output=" + os.path.join(generated, "transactions.fsdb"),
            "unit=1ns", "begin_time=0", "stream=bus.requests",
            "transactions=[{\"start_delta\":10,\"duration\":20,\"type\":\"npiFsdbwTransTransaction\",\"label\":\"req0\",\"tags\":[\"read\"]},{\"start_delta\":5,\"duration\":10,\"type\":\"npiFsdbwTransTransaction\",\"label\":\"rsp0\"}]",
            "relations=[{\"relation\":\"npiFsdbwRelParentChild\",\"master\":0,\"slave\":1}]",
        ])
    elif dynamic == "fsdb.writer.create_scope":
        arguments.extend([
            "output=" + os.path.join(generated, "hierarchy.fsdb"),
            "unit=1ns", "begin_time=0", "end_time_delta=100",
            "operations=[{\"op\":\"scope\",\"type\":\"npiFsdbScopeSvModule\",\"name\":\"top\"},{\"op\":\"scope\",\"type\":\"npiFsdbScopeSvModule\",\"name\":\"u_a\"},{\"op\":\"up\"},{\"op\":\"scope\",\"type\":\"npiFsdbScopeSvModule\",\"name\":\"u_b\"}]",
        ])

    for argument in arguments:
        command.extend(["--arg", argument])
    if case.get("limit"):
        command.extend(["--limit", "max_rows=100"])
    return command


def validate_module_rows(case, data):
    kind = case["kind"]
    ensure(data.get("kind") == kind, "module kind changed")
    count = data.get("count")
    if kind == "language_interfaces":
        ensure(count == 0, "pure SystemVerilog fixture must have zero language interfaces")
        return
    ensure(isinstance(count, int) and count >= case["minimum"], "module object count is below fixture minimum")
    items = data.get("items", []) or []
    rows = object_rows(data)

    expected_names = {
        "functions": {"add_with_bias"},
        "generate_scopes": {"g_wide"},
        "instances": {"u_alu"},
        "instances_in_generate": {"u_leaf"},
        "io": {"lhs", "rhs", "result"},
        "nets": {"result", "probe", "inverted_probe"},
        "parameters": {"WIDTH", "BIAS", "RESULT_WIDTH"},
        "ports": {"lhs", "rhs", "result"},
        "primitives": {"u_not"},
        "tasks": {"check_result"},
        "variables": {"sum"},
    }
    if kind in expected_names:
        names = {row.get("name") for row in rows}
        ensure(expected_names[kind].issubset(names), "module object names changed: %r" % sorted(names))

    if kind == "parameters":
        width = row_by_name(items, "WIDTH")
        bias = row_by_name(items, "BIAS")
        result_width = row_by_name(items, "RESULT_WIDTH")
        ensure(width is not None and str(width.get("values", {}).get("dec")) == "12", "WIDTH is not 12")
        ensure(bias is not None and str(bias.get("values", {}).get("dec")) == "1", "BIAS is not 1")
        ensure(result_width is not None and str(result_width.get("values", {}).get("dec")) == "12",
               "RESULT_WIDTH is not 12")
    elif kind == "ports":
        directions = {row.get("name"): row.get("direction") for row in rows}
        ensure(directions == {"lhs": "npiInput", "rhs": "npiInput", "result": "npiOutput"},
               "port directions changed: %r" % directions)
        for item in items:
            obj = item.get("object", {})
            connections = item.get("connections", {})
            ensure(obj.get("full_name") == "npi_fixture_top.u_alu." + obj.get("name", ""),
                   "port full name is not normalized")
            ensure(obj.get("parent_module") == "npi_fixture_top.u_alu", "port parent module is missing")
            ensure(connections.get("high") is not None and connections.get("low") is not None,
                   "port high/low connection evidence is missing")


def validate_response(case, response, command, context, cwd, log_base):
    ensure(response.get("api_version") == "kdebug.v1", "unexpected API version")
    ensure(response.get("action") == case["action"], "response action does not match request")
    data = response.get("data")
    ensure(isinstance(data, dict), "successful response has no data object")
    case_id = case["id"]

    if case_id == "npi.capabilities":
        domains = data.get("domains", [])
        names = {row.get("domain") for row in domains}
        ensure(names == EXPECTED_DOMAINS, "NPI capability domains changed: %r" % sorted(names))
        ensure(all(row.get("available") is True for row in domains), "one or more Tcl NPI domains are unavailable")
    elif case_id == "language.resolve":
        obj = data.get("object", {}).get("object", {})
        ensure(obj.get("full_name") == "npi_fixture_top.u_alu", "module instance did not resolve")
        ensure(obj.get("def_name") == "npi_fixture_alu", "module definition changed")
    elif case_id == "language.iterate":
        items = data.get("items", [])
        names = {row.get("object", {}).get("name") for row in items}
        ensure(names == {"WIDTH", "BIAS", "RESULT_WIDTH"}, "language parameter iterator changed")
        ensure(str(row_by_name(items, "WIDTH").get("values", {}).get("dec")) == "12", "WIDTH is not 12")
    elif case_id == "language.relate":
        obj = data.get("object", {}).get("object", {})
        ensure(obj.get("full_name") == "npi_fixture_top.result", "high connection did not resolve")
        ensure(obj.get("size") == 12, "high connection width is not 12")
    elif case_id == "language.value":
        ensure(str(data.get("value")) == "12", "effective WIDTH value is not 12")
    elif case_id == "module.find_instances":
        rows = object_rows(data, "instances")
        ensure(any(row.get("full_name") == "npi_fixture_top.u_alu" for row in rows),
               "definition lookup omitted u_alu")
    elif case_id == "module.inspect":
        module = data.get("module_object", {}).get("object", {})
        ensure(module.get("full_name") == "npi_fixture_top.u_alu", "inspect resolved the wrong module")
        sections = data.get("sections", {})
        required = {"parameters", "ports", "io", "nets", "variables", "functions",
                    "continuous_assignments", "always_processes"}
        ensure(required.issubset(set(sections)), "inspect is missing requested sections")
        parameter_rows = sections.get("parameters", [])
        width = row_by_name(parameter_rows, "WIDTH")
        ensure(width is not None and str(width.get("values", {}).get("dec")) == "12", "inspect WIDTH is not 12")
        port_rows = sections.get("ports", [])
        validate_module_rows({"kind": "ports", "minimum": 3},
                             {"kind": "ports", "count": len(port_rows), "items": port_rows})
    elif case["action"] == "module.objects":
        validate_module_rows(case, data)
    elif case_id == "netlist.resolve":
        obj = data.get("object", {})
        ensure(obj.get("full_name") == "npi_fixture_top.result[11:0]", "netlist result did not resolve")
        ensure(obj.get("size") == 12, "netlist result width is not 12")
    elif case_id == "netlist.iterate":
        ensure(data.get("count", 0) >= 7, "netlist iterator returned too few nets")
        ensure(any(row.get("full_name") == "npi_fixture_top.result[11:0]" for row in data.get("items", [])),
               "netlist iterator omitted result")
    elif case_id == "text.line":
        ensure(data.get("line") == 27, "Text Model returned the wrong line")
        ensure(data.get("content", "").strip() == "sum = add_with_bias(lhs, rhs);", "Text Model line changed")
    elif case_id == "text.words":
        words = {row.get("text") for row in data.get("words", [])}
        ensure({"sum", "add_with_bias", "lhs", "rhs"}.issubset(words), "Text Model tokens are incomplete")
        ensure(data.get("count", 0) >= 14, "Text Model returned too few words")
    elif case_id == "text.replace_line":
        output = data.get("output", "")
        ensure(os.path.isfile(output) and os.path.getsize(output) > 0, "patched source file was not written")
        with open(output, encoding="utf-8") as stream:
            lines = stream.readlines()
        ensure(len(lines) >= 27 and lines[26].strip() == "sum = lhs - rhs;", "patched line content is incorrect")
    elif case_id == "dm.add_net":
        ensure(data.get("name", "").startswith("debug_bus_"), "DM net name changed")
        ensure(data.get("packed_left") == 7 and data.get("packed_right") == 0, "DM packed range changed")
        ensure(nonempty_files(data.get("output_dir", "")), "DM add-net output is empty")
    elif case_id == "dm.clone_module":
        ensure(data.get("new_name", "").startswith("npi_fixture_alu_clone_"), "DM clone name changed")
        ensure(nonempty_files(data.get("output_dir", "")), "DM clone output is empty")
    elif case_id == "vcs.summary":
        ensure(data.get("compilation", {}).get("errors") == 0, "VCS database reports compile errors")
        ensure(data.get("design", {}).get("modules") == 3, "VCS database module count changed")
        ensure(data.get("tool", {}).get("version", "").startswith("O-2018.09"), "unexpected VCS version")
    elif case_id == "power.resolve":
        ensure(bool(data.get("object")), "Power Model resolve returned no object")
    elif case_id == "power.list":
        ensure(data.get("count", 0) >= 1, "Power Model iterator returned no elements")
    elif case_id == "crdb.resolve":
        obj = data.get("object", {})
        ensure(obj.get("full_name") == "npi_crdb_top.state", "CRDB resolved the wrong signal")
        ensure(obj.get("level") == 1, "CRDB RTL level changed")
    elif case_id == "crdb.correlates":
        ensure(data.get("count", 0) >= 1, "CRDB returned no correlated objects")
        ensure(any(row.get("full_name") == "npi_crdb_top.state" for row in data.get("correlated", [])),
               "CRDB correlation omitted state")
    elif case_id == "transaction.writer.create":
        output = data.get("output", "")
        ensure(os.path.isfile(output) and os.path.getsize(output) > 0, "transaction FSDB is empty")
        ensure(data.get("transaction_count") == 2 and data.get("relation_count") == 1,
               "transaction writer counts changed")
        ensure(data.get("end_time") == 45, "transaction writer end time changed")
    elif case_id == "fsdb.writer.create_scope":
        output = data.get("output", "")
        ensure(os.path.isfile(output) and os.path.getsize(output) > 0, "hierarchy FSDB is empty")
        ensure(data.get("scope_count") == 3 and data.get("up_count") == 1, "FSDB hierarchy counts changed")
        verify_command = [context["kdebug"], "--json", "action", "scope.list",
                          "--fsdb", output, "--path", "top", "--limit", "max_rows=100"]
        verify_started = time.monotonic()
        process = subprocess.Popen(verify_command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   universal_newlines=True)
        stdout, stderr = process.communicate()
        verify_elapsed = time.monotonic() - verify_started
        with open(log_base + ".verify.json", "w", encoding="utf-8") as stream:
            stream.write(stdout)
        with open(log_base + ".verify.stderr.log", "w", encoding="utf-8") as stream:
            stream.write(stderr)
        ensure(process.returncode == 0, "public scope.list could not reopen generated FSDB")
        verify = json.loads(stdout)
        ensure(verify.get("ok") is True, "generated FSDB verification response failed")
        ensure(set(verify.get("data", {}).get("scopes", [])) == {"top.u_a", "top.u_b"},
               "generated FSDB hierarchy is incomplete")
        return {"verification_elapsed_sec": verify_elapsed, "verification_action": "scope.list"}
    return {}


def run_attempt(case, iteration, context):
    case_slug = slug(case["id"])
    attempt_dir = os.path.join(context["output"], "attempts", case_slug)
    cwd = os.path.join(context["output"], "work", case_slug, "%04d" % iteration)
    os.makedirs(attempt_dir, exist_ok=True)
    os.makedirs(cwd, exist_ok=True)
    log_base = os.path.join(attempt_dir, "%04d" % iteration)
    command = build_command(case, iteration, context)
    started_at = utc_now()
    start = time.monotonic()
    process = subprocess.Popen(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               universal_newlines=True)
    stdout, stderr = process.communicate()
    elapsed = time.monotonic() - start
    ended_at = utc_now()

    stdout_file = log_base + ".stdout.json"
    stderr_file = log_base + ".stderr.log"
    with open(stdout_file, "w", encoding="utf-8") as stream:
        stream.write(stdout)
    with open(stderr_file, "w", encoding="utf-8") as stream:
        stream.write(stderr)

    response = None
    parse_error = ""
    try:
        response = json.loads(stdout)
    except Exception as error:
        parse_error = "%s: %s" % (type(error).__name__, error)

    status = "failed"
    error_code = ""
    invariant_error = ""
    extra = {}
    if isinstance(response, dict):
        error_code = (response.get("error") or {}).get("code", "")
        if response.get("ok") is True and process.returncode == 0:
            try:
                extra = validate_response(case, response, command, context, cwd, log_base)
                status = "passed"
            except Exception as error:
                invariant_error = "%s: %s" % (type(error).__name__, error)
        elif error_code == "LICENSE_UNAVAILABLE" and case.get("license_allowed"):
            status = "license_blocked"
        else:
            invariant_error = "action failed with %s" % (error_code or "unknown error")
    else:
        invariant_error = "response is not valid JSON: " + parse_error

    record = {
        "case_id": case["id"],
        "action": case["action"],
        "kind": case.get("kind", ""),
        "iteration": iteration,
        "status": status,
        "started_at": started_at,
        "ended_at": ended_at,
        "elapsed_sec": round(elapsed, 6),
        "exit_code": process.returncode,
        "error_code": error_code,
        "invariant_error": invariant_error,
        "stdout_sha256": sha256_file(stdout_file),
        "stdout_file": os.path.relpath(stdout_file, context["output"]),
        "stderr_file": os.path.relpath(stderr_file, context["output"]),
        "command": command,
    }
    record.update(extra)
    return record


def summarize_records(records, key_name):
    attempts = len(records)
    passed = sum(row["status"] == "passed" for row in records)
    blocked = sum(row["status"] == "license_blocked" for row in records)
    failed = sum(row["status"] == "failed" for row in records)
    durations = [row["elapsed_sec"] for row in records]
    if failed:
        status = "FAIL"
    elif passed == attempts:
        status = "PASS"
    elif blocked == attempts:
        status = "LICENSE_BLOCKED"
    else:
        status = "MIXED_PASS_LICENSE"
    return {
        key_name: records[0][key_name],
        "attempts": attempts,
        "passed": passed,
        "license_blocked": blocked,
        "failed": failed,
        "status": status,
        "elapsed_min_sec": round(min(durations), 6),
        "elapsed_avg_sec": round(sum(durations) / attempts, 6),
        "elapsed_p50_sec": round(percentile(durations, 0.50), 6),
        "elapsed_p95_sec": round(percentile(durations, 0.95), 6),
        "elapsed_max_sec": round(max(durations), 6),
    }


def write_csv(path, rows, fields):
    with open(path, "w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--kdebug", required=True)
    parser.add_argument("--fixture-root", required=True)
    parser.add_argument("--source-file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--iterations", type=int, required=True)
    parser.add_argument("--parallel", type=int, required=True)
    parser.add_argument("--setup-mode", choices=("fresh", "reused"), required=True)
    return parser.parse_args()


def main():
    args = parse_args()
    context = {
        "kdebug": os.path.abspath(args.kdebug),
        "fixture": os.path.abspath(args.fixture_root),
        "source": os.path.abspath(args.source_file),
        "output": os.path.abspath(args.output),
    }
    cases = make_cases()
    ensure(len(cases) == 36, "expected 36 independent stress cases")
    ensure(len({case["action"] for case in cases}) == 22, "expected 22 unique actions")

    command_text = os.environ.get("KDEBUG_STRESS_COMMAND", "")
    with open(os.path.join(context["output"], "stress-command.txt"), "w", encoding="utf-8") as stream:
        stream.write(command_text + "\n")

    all_records = []
    run_started = utc_now()
    wall_start = time.monotonic()
    for index, case in enumerate(cases, 1):
        print("[%02d/%02d] %-44s iterations=%d" % (index, len(cases), case["id"], args.iterations), flush=True)
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(args.parallel, args.iterations)) as pool:
            futures = [pool.submit(run_attempt, case, iteration, context)
                       for iteration in range(1, args.iterations + 1)]
            records = [future.result() for future in concurrent.futures.as_completed(futures)]
        records.sort(key=lambda row: row["iteration"])
        all_records.extend(records)
        counts = summarize_records(records, "case_id")
        print("         status=%s pass=%d blocked=%d fail=%d avg=%.3fs p95=%.3fs" % (
            counts["status"], counts["passed"], counts["license_blocked"], counts["failed"],
            counts["elapsed_avg_sec"], counts["elapsed_p95_sec"]), flush=True)

    run_ended = utc_now()
    wall_elapsed = time.monotonic() - wall_start
    all_records.sort(key=lambda row: ([case["id"] for case in cases].index(row["case_id"]), row["iteration"]))
    with open(os.path.join(context["output"], "stress-attempts.jsonl"), "w", encoding="utf-8") as stream:
        for row in all_records:
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    case_rows = []
    for case in cases:
        records = [row for row in all_records if row["case_id"] == case["id"]]
        result = summarize_records(records, "case_id")
        result["action"] = case["action"]
        result["kind"] = case.get("kind", "")
        case_rows.append(result)

    action_rows = []
    for action in sorted({case["action"] for case in cases}):
        records = [row for row in all_records if row["action"] == action]
        result = summarize_records(records, "action")
        result["case_count"] = len({row["case_id"] for row in records})
        action_rows.append(result)

    metric_fields = ["attempts", "passed", "license_blocked", "failed", "status",
                     "elapsed_min_sec", "elapsed_avg_sec", "elapsed_p50_sec",
                     "elapsed_p95_sec", "elapsed_max_sec"]
    write_csv(os.path.join(context["output"], "stress-results.csv"), case_rows,
              ["case_id", "action", "kind"] + metric_fields)
    write_csv(os.path.join(context["output"], "stress-action-results.csv"), action_rows,
              ["action", "case_count"] + metric_fields)

    passed_attempts = sum(row["status"] == "passed" for row in all_records)
    blocked_attempts = sum(row["status"] == "license_blocked" for row in all_records)
    failed_attempts = sum(row["status"] == "failed" for row in all_records)
    verification_calls = sum(bool(row.get("verification_action")) for row in all_records)
    failed_actions = sorted(row["action"] for row in action_rows if row["status"] == "FAIL")
    license_actions = sorted(row["action"] for row in action_rows if row["status"] == "LICENSE_BLOCKED")
    passed_actions = sorted(row["action"] for row in action_rows if row["status"] == "PASS")
    summary = {
        "schema": "kdebug.npi-actions.vm-stress.v1",
        "run": {
            "started_at": run_started,
            "ended_at": run_ended,
            "wall_elapsed_sec": round(wall_elapsed, 6),
            "command": command_text,
            "iterations_per_case": args.iterations,
            "parallelism": args.parallel,
            "setup_mode": args.setup_mode,
            "harness_timeout_sec": None,
        },
        "environment": {
            "user": os.environ.get("USER", ""),
            "hostname": socket.gethostname(),
            "platform": platform.platform(),
            "python": platform.python_version(),
            "verdi_home": os.environ.get("VERDI_HOME", ""),
            "vcs_home": os.environ.get("VCS_HOME", ""),
            "kdebug": context["kdebug"],
            "kdebug_sha256": sha256_file(context["kdebug"]),
            "source_file": context["source"],
            "source_sha256": sha256_file(context["source"]),
            "fixture_root": context["fixture"],
        },
        "scope": {
            "unique_actions": 22,
            "independent_cases": 36,
            "module_object_kinds": 15,
            "public_cli_only": True,
            "direct_tcl_or_npi_calls": 0,
        },
        "totals": {
            "attempts": len(all_records),
            "verification_calls": verification_calls,
            "public_cli_invocations": len(all_records) + verification_calls,
            "passed": passed_attempts,
            "license_blocked": blocked_attempts,
            "failed": failed_attempts,
            "passed_actions": len(passed_actions),
            "license_blocked_actions": len(license_actions),
            "failed_actions": len(failed_actions),
        },
        "passed_action_names": passed_actions,
        "license_blocked_action_names": license_actions,
        "failed_action_names": failed_actions,
        "unexpected_failures": [row for row in all_records if row["status"] == "failed"],
        "action_results": action_rows,
        "case_results": case_rows,
        "accepted": failed_attempts == 0 and set(license_actions).issubset({"power.resolve", "power.list"}),
    }
    with open(os.path.join(context["output"], "stress-summary.json"), "w", encoding="utf-8") as stream:
        json.dump(summary, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")

    print("SUMMARY attempts=%d passed=%d license_blocked=%d failed=%d wall=%.3fs" % (
        len(all_records), passed_attempts, blocked_attempts, failed_attempts, wall_elapsed), flush=True)
    print("RESULT %s" % os.path.join(context["output"], "stress-summary.json"), flush=True)
    return 0 if summary["accepted"] else 1


if __name__ == "__main__":
    sys.exit(main())
