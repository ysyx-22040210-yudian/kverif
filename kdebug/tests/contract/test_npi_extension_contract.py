from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import jsonschema
import pytest


NEW_NPI_ACTIONS = {
    "npi.capabilities",
    "language.resolve",
    "language.iterate",
    "language.relate",
    "language.value",
    "module.objects",
    "module.find_instances",
    "module.inspect",
    "module.inspect_batch",
    "port.trace_batch",
    "netlist.resolve",
    "netlist.iterate",
    "text.line",
    "text.words",
    "text.replace_line",
    "dm.add_net",
    "dm.clone_module",
    "vcs.summary",
    "power.resolve",
    "power.list",
    "crdb.resolve",
    "crdb.correlates",
    "transaction.writer.create",
    "fsdb.writer.create_scope",
}


MODULE_OBJECT_KINDS = {
    "continuous_assignments": "npi_mod_inst_get_cont_assign",
    "functions": "npi_mod_inst_get_func",
    "generate_scopes": "npi_mod_inst_get_gen_scope",
    "instances": "npi_mod_inst_get_instance",
    "instances_in_generate": "npi_mod_inst_get_instance_in_gen_scope",
    "io": "npi_mod_inst_get_io",
    "language_interfaces": "npi_mod_inst_get_lang_interface",
    "nets": "npi_mod_inst_get_net",
    "parameters": "npi_mod_inst_get_parameter",
    "ports": "npi_mod_inst_get_port",
    "primitives": "npi_mod_inst_get_primitive",
    "always_processes": "npi_mod_inst_get_process_always",
    "initial_processes": "npi_mod_inst_get_process_init",
    "tasks": "npi_mod_inst_get_task",
    "variables": "npi_mod_inst_get_var",
}


def _load_engine(kdebug_root: Path):
    path = kdebug_root / "tcl_engine" / "kdebug_engine.py"
    spec = importlib.util.spec_from_file_location("kdebug_tcl_engine_contract", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.contract
def test_new_actions_have_explicit_tcl_dispatch(kdebug_root: Path) -> None:
    script = (kdebug_root / "tcl_engine" / "kdebug_npi.tcl").read_text(encoding="utf-8")
    for action in NEW_NPI_ACTIONS:
        assert '$action eq "%s"' % action in script
    assert "eval " not in script


@pytest.mark.contract
def test_module_action_maps_every_documented_module_getter(kdebug_root: Path) -> None:
    script = (kdebug_root / "tcl_engine" / "kdebug_npi.tcl").read_text(
        encoding="utf-8"
    )
    for kind, command in MODULE_OBJECT_KINDS.items():
        assert f"{kind} {{return ::npi_L1::{command}}}" in script
    assert "::npi_L1::npi_mod_define_get_inst" in script


@pytest.mark.contract
def test_transaction_plan_is_typed_and_hex_encoded(kdebug_root: Path, tmp_path: Path) -> None:
    engine = _load_engine(kdebug_root)
    transaction_path, tag_path, relation_path = engine.prepare_transaction_plans(
        {
            "transactions": [
                {
                    "start_delta": 10,
                    "duration": 20,
                    "type": "npiFsdbwTransTransaction",
                    "label": "request zero",
                    "tags": ["read request"],
                },
                {
                    "start_delta": 5,
                    "duration": 10,
                    "type": "npiFsdbwTransTransaction",
                    "label": "response zero",
                },
            ],
            "relations": [
                {"relation": "npiFsdbwRelParentChild", "master": 0, "slave": 1}
            ],
        },
        str(tmp_path),
    )

    transaction_rows = Path(transaction_path).read_text(encoding="utf-8").splitlines()
    assert transaction_rows[0].split("\t")[:3] == ["10", "20", "npiFsdbwTransTransaction"]
    assert bytes.fromhex(transaction_rows[0].split("\t")[3]).decode("utf-8") == "request zero"
    tag_fields = Path(tag_path).read_text(encoding="utf-8").strip().split("\t")
    assert tag_fields[0] == "0"
    assert bytes.fromhex(tag_fields[1]).decode("utf-8") == "read request"
    relation_fields = Path(relation_path).read_text(encoding="utf-8").strip().split("\t")
    assert bytes.fromhex(relation_fields[0]).decode("utf-8") == "npiFsdbwRelParentChild"
    assert relation_fields[1:] == ["0", "1"]


@pytest.mark.contract
def test_transaction_plan_rejects_invalid_relation(kdebug_root: Path, tmp_path: Path) -> None:
    engine = _load_engine(kdebug_root)
    with pytest.raises(ValueError, match="two different transactions"):
        engine.prepare_transaction_plans(
            {
                "transactions": [{"duration": 1}],
                "relations": [{"relation": "related", "master": 0, "slave": 0}],
            },
            str(tmp_path),
        )


@pytest.mark.contract
def test_scope_plan_preserves_hierarchy_operations(kdebug_root: Path, tmp_path: Path) -> None:
    engine = _load_engine(kdebug_root)
    path = engine.prepare_scope_plan(
        {
            "operations": [
                {"op": "scope", "type": "npiFsdbScopeSvModule", "name": "top"},
                {"op": "scope", "type": "npiFsdbScopeSvModule", "name": "u_a"},
                {"op": "up"},
                {"op": "scope", "type": "npiFsdbScopeSvModule", "name": "u_b"},
            ]
        },
        str(tmp_path),
    )
    rows = Path(path).read_text(encoding="utf-8").splitlines()
    assert [row.split("\t")[0] for row in rows] == ["scope", "scope", "up", "scope"]
    assert bytes.fromhex(rows[0].split("\t")[2]).decode("utf-8") == "top"


@pytest.mark.contract
def test_scope_plan_rejects_up_above_root(kdebug_root: Path, tmp_path: Path) -> None:
    engine = _load_engine(kdebug_root)
    with pytest.raises(ValueError, match="above the root"):
        engine.prepare_scope_plan({"operations": [{"op": "up"}]}, str(tmp_path))


@pytest.mark.contract
def test_string_batch_plan_is_hex_encoded_and_ordered(
    kdebug_root: Path, tmp_path: Path
) -> None:
    engine = _load_engine(kdebug_root)
    path = engine.prepare_string_batch_plan(
        {"signals": ["top.u_a.ready[0]", "top.u_b.valid"]},
        "signals",
        str(tmp_path),
        "signals.tsv",
    )
    rows = Path(path).read_text(encoding="utf-8").splitlines()
    assert [bytes.fromhex(row).decode("utf-8") for row in rows] == [
        "top.u_a.ready[0]",
        "top.u_b.valid",
    ]


@pytest.mark.contract
def test_port_trace_environment_accepts_all_ports_and_rejects_bad_selects(
    kdebug_root: Path, tmp_path: Path
) -> None:
    engine = _load_engine(kdebug_root)
    env = engine.prepare_port_trace_environment(
        {"module": "MSHR", "stop_instances": ["top.u_stop"]},
        {},
        {"daidir": "/data/build/simv.daidir"},
        str(tmp_path),
    )
    assert Path(env["KDEBUG_TCL_PORT_PLAN"]).read_text(encoding="utf-8") == ""
    stop_row = Path(env["KDEBUG_TCL_STOP_INSTANCE_PLAN"]).read_text(
        encoding="utf-8"
    ).strip()
    assert bytes.fromhex(stop_row).decode("utf-8") == "top.u_stop"
    assert env["KDEBUG_TCL_MAX_PARENT_DEPTH"] == "16"
    assert env["KDEBUG_TCL_MAX_NODES"] == "20000"

    with pytest.raises(ValueError, match="valid port or bit-select"):
        engine.prepare_port_trace_environment(
            {"module": "MSHR", "ports": ["io_id; exec bad"]},
            {},
            {"daidir": "/data/build/simv.daidir"},
            str(tmp_path),
        )


@pytest.mark.contract
def test_port_trace_response_schema_matches_runtime_required_fields(
    kdebug_root: Path,
) -> None:
    schema = json.loads(
        (kdebug_root / "schemas" / "v1" / "actions" /
         "port.trace_batch.response.schema.json").read_text(encoding="utf-8")
    )
    example = json.loads(
        (kdebug_root / "examples" / "responses" /
         "port.trace_batch.basic.json").read_text(encoding="utf-8")
    )
    validator = jsonschema.Draft202012Validator(schema)
    validator.validate(example)

    missing_effective = json.loads(json.dumps(example))
    del missing_effective["data"]["evidence"][0]["effective"]
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(missing_effective)

    missing_role = json.loads(json.dumps(example))
    del missing_role["data"]["evidence"][0]["role"]
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(missing_role)

    empty_trace_field = json.loads(json.dumps(example))
    empty_trace_field["data"]["full_rows"][0]["signal_full_name"] = ""
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(empty_trace_field)

    empty_error_field = json.loads(json.dumps(example))
    empty_error_field["data"]["errors"] = [
        {"scope": "port", "code": "", "message": "row limit"}
    ]
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(empty_error_field)


@pytest.mark.contract
def test_port_trace_batch_runs_one_verdi_process_and_postprocesses_evidence(
    kdebug_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = _load_engine(kdebug_root)
    calls = []
    planned_ports = []

    class FakePopen:
        returncode = 0

        def __init__(self, command, **kwargs):
            self.command = command
            self.env = kwargs["env"]
            calls.append(self)

        def communicate(self, timeout=None):
            planned_ports.extend(
                bytes.fromhex(row).decode("utf-8")
                for row in Path(self.env["KDEBUG_TCL_PORT_PLAN"])
                .read_text(encoding="utf-8")
                .splitlines()
            )
            port_path = "top.u_dut.a[0]"
            response = {
                "ok": True,
                "data": {
                    "module": "Dut",
                    "requested_ports": ["a[0]"],
                    "full_rows": [_port_row("a[0]", "Const:1'b1")],
                    "boundary_rows": [_port_row("a[0]", "Const:1'b1")],
                    "evidence": [
                        _constant_evidence(
                            port_path, "Const:1'b1", "source_port_connection"
                        )
                    ],
                    "errors": [],
                    "stats": {"processed_instances": 1},
                    "truncated": False,
                },
            }
            Path(self.env["KDEBUG_TCL_RESPONSE_JSON"]).write_text(
                json.dumps(response), encoding="utf-8"
            )
            return "", ""

    monkeypatch.setattr(engine, "find_verdi", lambda: "/fake/verdi")
    monkeypatch.setattr(engine.subprocess, "Popen", FakePopen)
    ok, data = engine.run_action(
        {
            "action": "port.trace_batch",
            "target": {"daidir": "/data/build/simv.daidir"},
            "args": {"module": "Dut", "ports": ["a[0]"]},
        },
        {"target": {}},
    )
    assert ok is True
    assert len(calls) == 1
    assert planned_ports == ["a[0]"]
    assert calls[0].command[-2:] == ["-dbdir", "/data/build/simv.daidir"]
    assert data["full_rows"][0]["signal_full_name"] == "Const:1'b1"
    assert data["boundary_rows"][0]["signal_full_name"] == "Const:1'b1"
    assert data["evidence"][0]["effective"] is True
    assert data["evidence"][0]["provenance"]["path"] == [
        "top.u_dut.a[0]",
        "Const:1'b1",
    ]


def _constant_evidence(port_path: str, value: str, method: str) -> dict:
    candidate = method == "source_port_connection"
    return {
        "kind": "constant",
        "value": value,
        "method": method,
        "role": "driver",
        "port_path": port_path,
        "const_full_path": "%s<-%s" % (port_path, value),
        "effective_candidate": candidate,
        "constant": {"value": value, "effective": candidate},
        "provenance": {
            "origin": method,
            "unconditional": candidate,
            "path": [port_path, value],
            "source": {"file": "rtl/top.sv", "line": ""},
        },
        "fields": {"role": "driver", "port_path": port_path},
    }


def _port_row(port: str, signal: str) -> dict:
    return {
        "inst_full_name": "top.u_dut",
        "port_name": port,
        "port_dir": "input",
        "role": "driver",
        "signal_full_name": signal,
    }


@pytest.mark.contract
def test_port_trace_fail_closed_for_expression_leaf_constants(kdebug_root: Path) -> None:
    engine = _load_engine(kdebug_root)
    port_path = "top.u_dut.a"
    data = engine.postprocess_port_trace_data(
        {
            "module": "Dut",
            "requested_ports": ["a"],
            "full_rows": [_port_row("a", "Const:1'b1"), _port_row("a", "Const:1'b0")],
            "boundary_rows": [],
            "evidence": [
                _constant_evidence(port_path, "Const:1'b1", "npi_trace_driver_by_hdl"),
                _constant_evidence(port_path, "Const:1'b0", "npi_trace_driver_by_hdl"),
            ],
            "errors": [],
            "stats": {"processed_instances": 1},
            "truncated": False,
        }
    )
    assert [row["signal_full_name"] for row in data["full_rows"]] == [
        "TRACE_LIMIT_REACHED:constant_provenance_unverified"
    ]
    assert {error["code"] for error in data["errors"]} == {
        "CONSTANT_PROVENANCE_UNVERIFIED"
    }
    assert all(not item["effective"] for item in data["evidence"])
    assert data["truncated"] is True


@pytest.mark.contract
def test_port_trace_conflict_and_cross_surface_mix_are_fail_closed(
    kdebug_root: Path,
) -> None:
    engine = _load_engine(kdebug_root)
    port_path = "top.u_dut.a"
    data = engine.postprocess_port_trace_data(
        {
            "module": "Dut",
            "requested_ports": ["a"],
            "full_rows": [
                _port_row("a", "Const:1'b1"),
                _port_row("a", "Const:1'b0"),
                _port_row("a", "top.sel_data"),
            ],
            "boundary_rows": [_port_row("a", "Const:1'b1")],
            "evidence": [
                _constant_evidence(port_path, "Const:1'b1", "source_port_connection"),
                _constant_evidence(port_path, "Const:1'b0", "source_port_connection"),
            ],
            "errors": [],
            "stats": {"processed_instances": 1},
            "truncated": False,
        }
    )
    assert [row["signal_full_name"] for row in data["full_rows"]] == ["top.sel_data"]
    assert [row["signal_full_name"] for row in data["boundary_rows"]] == [
        "TRACE_LIMIT_REACHED:constant_driver_conflict"
    ]
    assert {error["code"] for error in data["errors"]} == {
        "CONSTANT_DRIVER_CONFLICT"
    }
    assert all(not item["effective"] for item in data["evidence"])


@pytest.mark.contract
def test_port_trace_constant_syntax_normalizes_equivalent_zero(kdebug_root: Path) -> None:
    engine = _load_engine(kdebug_root)
    assert engine.port_trace_constant_semantics("'b0") == "bit:0"
    assert engine.port_trace_constant_semantics("1'b0") == "bit:0"
    assert engine.port_trace_constant_semantics("'h1") == "bit:1"


@pytest.mark.contract
def test_port_trace_row_limit_deactivates_unpublished_constant_evidence(
    kdebug_root: Path,
) -> None:
    engine = _load_engine(kdebug_root)
    data = engine.postprocess_port_trace_data(
        {
            "module": "Dut",
            "requested_ports": ["a"],
            "full_rows": [_port_row("a", "TRACE_LIMIT_REACHED:row_limit")],
            "boundary_rows": [],
            "evidence": [
                _constant_evidence(
                    "top.u_dut.a", "Const:1'b1", "source_port_connection"
                )
            ],
            "errors": [],
            "stats": {"processed_instances": 1},
            "truncated": True,
        }
    )
    assert data["full_rows"][0]["signal_full_name"] == (
        "TRACE_LIMIT_REACHED:row_limit"
    )
    assert data["evidence"][0]["effective"] is False
    assert data["evidence"][0]["constant"]["effective"] is False
    assert data["evidence"][0]["provenance"]["unconditional"] is False
    assert data["evidence"][0]["rejection_reason"] == "row_not_published"
    assert data["stats"]["trace_limit_marker_count"] == 1


@pytest.mark.contract
def test_port_trace_tcl_row_budget_is_strict_and_zero_is_unlimited(
    kdebug_root: Path, tmp_path: Path
) -> None:
    tclsh = shutil.which("tclsh")
    if not tclsh:
        pytest.skip("tclsh is unavailable")
    wrapper = tmp_path / "port_trace_row_limit.tcl"
    wrapper.write_text(
        """
source {%s}
set kdebug_port_trace_max_rows 2
set kdebug_port_trace_full_rows {}
set kdebug_port_trace_boundary_rows {}
set kdebug_port_trace_row_limit_surfaces {}
set kdebug_port_trace_truncated 0
foreach signal {top.a top.b top.c} {
    write_trace_row __KDEBUG_FULL__ top.u_dut a input driver $signal
    write_trace_row __KDEBUG_BOUNDARY__ top.u_dut a input driver $signal
}
puts "full=[llength $kdebug_port_trace_full_rows]:[dict get [lindex $kdebug_port_trace_full_rows end] signal_full_name]"
puts "boundary=[llength $kdebug_port_trace_boundary_rows]:[dict get [lindex $kdebug_port_trace_boundary_rows end] signal_full_name]"
puts "limited=$kdebug_port_trace_truncated"

set kdebug_port_trace_max_rows 0
set kdebug_port_trace_full_rows {}
set kdebug_port_trace_row_limit_surfaces {}
set kdebug_port_trace_truncated 0
foreach signal {top.a top.b top.c} {
    write_trace_row __KDEBUG_FULL__ top.u_dut a input driver $signal
}
puts "unlimited=[llength $kdebug_port_trace_full_rows]:$kdebug_port_trace_truncated"
"""
        % (kdebug_root / "tcl_engine" / "kdebug_port_trace.tcl").as_posix(),
        encoding="utf-8",
    )
    completed = subprocess.run(
        [tclsh, str(wrapper)], capture_output=True, text=True, timeout=20
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.splitlines() == [
        "full=2:TRACE_LIMIT_REACHED:row_limit",
        "boundary=2:TRACE_LIMIT_REACHED:row_limit",
        "limited=1",
        "unlimited=3:0",
    ]


@pytest.mark.contract
def test_port_trace_exact_bit_must_be_in_bounds_before_seen(
    kdebug_root: Path, tmp_path: Path
) -> None:
    tclsh = shutil.which("tclsh")
    if not tclsh:
        pytest.skip("tclsh is unavailable")
    wrapper = tmp_path / "port_trace_exact_bit.tcl"
    wrapper.write_text(
        """
source {%s}
namespace eval ::npi_L1 {}

rename get_instance_path __real_get_instance_path
proc get_instance_path {hdl} {return top.u_dut}
rename get_io_handles __real_get_io_handles
proc get_io_handles {inst} {return {PORT}}
rename get_port_handles __real_get_port_handles
proc get_port_handles {inst} {return {PORT}}
rename get_port_name __real_get_port_name
proc get_port_name {hdl} {return a}
rename get_port_direction __real_get_port_direction
proc get_port_direction {hdl} {return input}
rename get_handle_size __real_get_handle_size
proc get_handle_size {hdl} {
    if {$hdl eq "PORT"} {return 8}
    if {$hdl eq "BIT7"} {return 1}
    return ""
}
rename get_handle_source_file __real_get_handle_source_file
proc get_handle_source_file {hdl} {return ""}
rename hdl_to_name __real_hdl_to_name
proc hdl_to_name {hdl args} {
    if {$hdl eq "PORT"} {return top.u_dut.a}
    if {$hdl eq "BIT7"} {return {top.u_dut.a[7]}}
    return ""
}

proc ::npi_L1::npi_find_inst_with_def_wildcard {scope module result_var} {
    upvar 1 $result_var result
    set result {INST}
}
proc ::npi_L1::npi_inst_port_2_high_conn_sig {inst result_var} {
    upvar 1 $result_var result
    set result {}
}
proc ::npi_L1::npi_inst_port_2_low_conn_sig {inst result_var} {
    upvar 1 $result_var result
    set result {}
}
proc ::npi_L1::npi_nl_sig_handle_by_name {name} {
    if {[string equal $name {top.u_dut.a[7]}]} {return BIT7}
    return ""
}
proc npi_nl_handle_by_index {args} {return ""}

proc run_case {requested} {
    lassign [kdebug_port_trace_run Dut [list $requested] {} "" 1 1 1 16 2 1 100 100 100 0 0] ok code message processed skipped
    set error_codes {}
    foreach record $::kdebug_port_trace_errors {
        lappend error_codes [dict get $record code]
    }
    puts "$requested|$ok|[llength $::kdebug_port_trace_full_rows]|[join $error_codes ,]|[dict exists $::kdebug_port_trace_seen_ports \"top.u_dut|$requested\"]"
}
run_case {a[999]}
run_case {a[6]}
run_case {a[7]}
"""
        % (kdebug_root / "tcl_engine" / "kdebug_port_trace.tcl").as_posix(),
        encoding="utf-8",
    )
    completed = subprocess.run(
        [tclsh, str(wrapper)], capture_output=True, text=True, timeout=20
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.splitlines() == [
        "a[999]|1|0|PORT_NOT_FOUND|0",
        "a[6]|1|2||1",
        "a[7]|1|2||1",
    ]


@pytest.mark.contract
def test_port_trace_tcl_wrapper_emits_distinct_surfaces_and_evidence(
    kdebug_root: Path, tmp_path: Path
) -> None:
    tclsh = shutil.which("tclsh")
    if not tclsh:
        pytest.skip("tclsh is unavailable")
    port_plan = tmp_path / "ports.tsv"
    stop_plan = tmp_path / "stops.tsv"
    response_path = tmp_path / "response.json"
    npi_dir = tmp_path / "npi"
    npi_dir.mkdir()
    (npi_dir / "npi_L1.tcl").write_text("", encoding="utf-8")
    port_plan.write_bytes(("%s\n" % "a".encode("utf-8").hex()).encode("ascii"))
    stop_plan.write_bytes(b"")
    wrapper = tmp_path / "port_trace_stub.tcl"
    npi_script = (kdebug_root / "tcl_engine" / "kdebug_npi.tcl").as_posix()
    wrapper.write_text(
        """
rename source __real_source
proc source {path} {
    if {[string match *npi_L1.tcl $path]} {return}
    if {[file tail $path] eq "kdebug_port_trace.tcl"} {
        uplevel 1 [list __real_source $path]
        rename kdebug_port_trace_run kdebug_port_trace_run_legacy
        proc kdebug_port_trace_run {module ports stops source fallback full boundary args} {
            set ::kdebug_port_trace_full_rows [list [dict create inst_full_name top.u_dut port_name a port_dir input role driver signal_full_name top.src]]
            set ::kdebug_port_trace_boundary_rows [list [dict create inst_full_name top.u_dut port_name a port_dir input role driver signal_full_name top.boundary]]
            set fields [dict create role driver instance top.u_dut port a port_path top.u_dut.a source_file rtl/top.sv]
            set ::kdebug_port_trace_evidence [list [dict create method source_port_connection value Const:1'b1 const_full_path top.u_dut.a<-Const:1'b1 fields $fields]]
            set ::kdebug_port_trace_errors {}
            set ::kdebug_port_trace_truncated 0
            return [list 1 "" "" 1 0]
        }
        return
    }
    uplevel 1 [list __real_source $path]
}
rename exit __real_exit
proc exit args {return}
set env(NPIL1_PATH) {%s}
set env(KDEBUG_TCL_ACTION) port.trace_batch
set env(KDEBUG_TCL_MODULE) Dut
set env(KDEBUG_TCL_PORT_PLAN) {%s}
set env(KDEBUG_TCL_STOP_INSTANCE_PLAN) {%s}
set env(KDEBUG_TCL_RESPONSE_JSON) {%s}
set env(KDEBUG_TCL_SOURCE_FALLBACK) 1
set env(KDEBUG_TCL_INCLUDE_FULL) 1
set env(KDEBUG_TCL_INCLUDE_BOUNDARY) 1
set env(KDEBUG_TCL_MAX_PARENT_DEPTH) 16
set env(KDEBUG_TCL_MAX_ASSIGN_DEPTH) 2
set env(KDEBUG_TCL_MAX_EXPR_DEPTH) 1
set env(KDEBUG_TCL_MAX_NODES) 20000
set env(KDEBUG_TCL_MAX_EDGES) 100000
set env(KDEBUG_TCL_MAX_API_RESULTS) 20000
set env(KDEBUG_TCL_MAX_ROWS) 20000
__real_source {%s}
"""
        % (
            npi_dir.as_posix(),
            port_plan.as_posix(),
            stop_plan.as_posix(),
            response_path.as_posix(),
            npi_script,
        ),
        encoding="utf-8",
    )
    completed = subprocess.run(
        [tclsh, str(wrapper)], capture_output=True, text=True, timeout=20
    )
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(response_path.read_text(encoding="utf-8"))
    assert payload["ok"] is True
    assert payload["data"]["full_rows"][0]["signal_full_name"] == "top.src"
    assert payload["data"]["boundary_rows"][0]["signal_full_name"] == "top.boundary"
    evidence = payload["data"]["evidence"][0]
    assert evidence["provenance"]["path"] == ["top.u_dut.a", "Const:1'b1"]


@pytest.mark.contract
def test_tcl_timeout_uses_new_session_and_bounded_cleanup(
    kdebug_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = _load_engine(kdebug_root)
    calls = []

    class FakePopen:
        returncode = -15

        def __init__(self, command, **kwargs):
            self.env = kwargs["env"]
            self.kwargs = kwargs
            self.communicate_calls = 0
            calls.append(self)

        def communicate(self, timeout=None):
            assert timeout is not None
            self.communicate_calls += 1
            if self.communicate_calls == 1:
                raise subprocess.TimeoutExpired("verdi", timeout)
            return "", "timed out"

        def terminate(self):
            return None

        def kill(self):
            return None

    monkeypatch.setattr(engine, "find_verdi", lambda: "/fake/verdi")
    monkeypatch.setattr(engine.subprocess, "Popen", FakePopen)
    monkeypatch.setattr(engine, "process_ids_with_run_token", lambda token: [])
    ok, error = engine.run_tcl_npi(
        {
            "action": "trace.driver",
            "target": {"daidir": "/data/build/simv.daidir"},
            "args": {"signal": "top.a"},
            "limits": {"timeout_ms": 1},
        },
        {"target": {}},
    )
    assert ok is False
    assert error["code"] == "TCL_NPI_TIMEOUT"
    assert calls[0].kwargs["start_new_session"] is True
    assert calls[0].env["KDEBUG_RUN_TOKEN"]
    assert calls[0].communicate_calls == 2


@pytest.mark.contract
@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="requires Linux /proc")
def test_timeout_cleanup_kills_reparented_run_token_process(
    kdebug_root: Path, tmp_path: Path
) -> None:
    engine = _load_engine(kdebug_root)
    child_pid_path = tmp_path / "child.pid"
    token = "kdebug-cleanup-test-%d-%d" % (os.getpid(), int(time.time() * 1000000000))
    child_code = "import time; time.sleep(60)"
    parent_code = (
        "import os,subprocess,sys,time; "
        "p=subprocess.Popen([sys.executable,'-c',%r], start_new_session=True); "
        "open(%r,'w').write(str(p.pid)); time.sleep(60)"
    ) % (child_code, str(child_pid_path))
    env = dict(os.environ)
    env["KDEBUG_RUN_TOKEN"] = token
    proc = subprocess.Popen(
        [sys.executable, "-c", parent_code],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        start_new_session=True,
        text=True,
    )
    try:
        deadline = time.time() + 5
        while not child_pid_path.exists() and time.time() < deadline:
            time.sleep(0.05)
        assert child_pid_path.exists()
        child_pid = int(child_pid_path.read_text(encoding="utf-8"))
        engine.terminate_tcl_process_run(proc, token, grace_seconds=0.2)
        deadline = time.time() + 3
        child_proc = Path("/proc/%d" % child_pid)
        while (engine.process_ids_with_run_token(token) or child_proc.exists()) and time.time() < deadline:
            time.sleep(0.05)
        assert engine.process_ids_with_run_token(token) == []
        assert not child_proc.exists()
    finally:
        engine.cleanup_run_token_orphans(token, grace_seconds=0.1)
        if proc.poll() is None:
            proc.kill()
            proc.communicate(timeout=2)


@pytest.mark.contract
def test_module_inspect_batch_runs_one_verdi_process(
    kdebug_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = _load_engine(kdebug_root)
    calls = []
    planned_modules = []

    class FakePopen:
        returncode = 0

        def __init__(self, command, **kwargs):
            self.env = kwargs["env"]
            calls.append(command)

        def communicate(self, timeout=None):
            planned_modules.extend(
                bytes.fromhex(row).decode("utf-8")
                for row in Path(self.env["KDEBUG_TCL_BATCH_PLAN"])
                .read_text(encoding="utf-8")
                .splitlines()
            )
            response = {
                "ok": True,
                "data": {
                    "inspections": [
                        {
                            "module": "top.u_a",
                            "ok": True,
                            "data": {"module": "top.u_a", "truncated": False},
                            "error": None,
                        },
                        {
                            "module": "top.u_missing",
                            "ok": False,
                            "data": None,
                            "error": {"code": "MODULE_NOT_FOUND", "message": "missing"},
                        },
                    ]
                },
            }
            Path(self.env["KDEBUG_TCL_RESPONSE_JSON"]).write_text(
                json.dumps(response), encoding="utf-8"
            )
            return "", ""

        def kill(self):
            return None

    monkeypatch.setattr(engine, "find_verdi", lambda: "/fake/verdi")
    monkeypatch.setattr(engine.subprocess, "Popen", FakePopen)
    request = {
        "api_version": "kdebug.internal.v1",
        "action": "module.inspect_batch",
        "target": {"daidir": "/data/build/simv.daidir"},
        "args": {
            "modules": ["top.u_a", "top.u_missing"],
            "sections": ["parameters", "ports"],
        },
    }
    ok, data = engine.run_action(request, {"target": request["target"]})

    assert ok is True
    assert len(calls) == 1
    assert planned_modules == ["top.u_a", "top.u_missing"]
    assert data["summary"] == {
        "module_count": 2,
        "success_count": 1,
        "error_count": 1,
        "truncated": False,
    }


@pytest.mark.contract
def test_raw_tcl_response_fields_encode_boolean_markers(kdebug_root: Path) -> None:
    script = (kdebug_root / "tcl_engine" / "kdebug_npi.tcl").read_text(
        encoding="utf-8"
    )
    unencoded = re.findall(
        r'^\s+truncated \[expr \{\$truncated \? "__JSON_TRUE__" : "__JSON_FALSE__"\}\] \\$',
        script,
        flags=re.MULTILINE,
    )
    assert unencoded == []


@pytest.mark.contract
def test_source_filelist_target_builds_controlled_verdi_argv(
    kdebug_root: Path, tmp_path: Path
) -> None:
    engine = _load_engine(kdebug_root)
    filelist = tmp_path / "run.f"
    upf = tmp_path / "design.upf"
    filelist.write_text("design.sv\n", encoding="utf-8")
    upf.write_text("", encoding="utf-8")

    argv = engine.design_args_for_target(
        {
            "filelist": str(filelist),
            "upf": str(upf),
            "upf_version": "2.0",
            "defines": ["NOVAS_UPF_PKG"],
            "top": "system",
        },
        "power.resolve",
    )
    assert argv == [
        "+define+NOVAS_UPF_PKG",
        "-sv",
        "-f",
        str(filelist),
        "-upf2.0",
        str(upf),
        "-top",
        "system",
    ]
    assert engine.design_workdir_for_target(
        {"filelist": str(filelist)}, "power.resolve", "/tmp/fallback"
    ) == str(tmp_path)


@pytest.mark.contract
def test_verdi_license_failure_is_infrastructure_error(kdebug_root: Path) -> None:
    engine = _load_engine(kdebug_root)
    error = engine.classify_verdi_license_error(
        "Failed to check out features PowerAwareAnalysis, or the number of licensed users was already reached.",
        "",
        0,
    )
    assert error["code"] == "LICENSE_UNAVAILABLE"
    assert error["feature"] == "PowerAwareAnalysis"


@pytest.mark.contract
def test_novas_config_warning_is_not_a_design_db_error(kdebug_root: Path) -> None:
    engine = _load_engine(kdebug_root)
    warning = "Cannot open /tmp/novas.conf for read access"
    assert engine.classify_verdi_no_response(warning, "", 0)["code"] == "TCL_NPI_NO_RESPONSE"
    combined = warning + "\nCannot open /data/missing/simv.daidir for read access"
    assert engine.classify_verdi_no_response(combined, "", 0)["code"] == "DESIGN_DB_ACCESS_FAILED"


@pytest.mark.contract
def test_crdb_level_uses_verdi_2018_enum_with_manual_fallback(
    kdebug_root: Path,
) -> None:
    script = (kdebug_root / "tcl_engine" / "kdebug_npi.tcl").read_text(
        encoding="utf-8"
    )
    assert '"npiCrdbLevelRTL" : "npiCrdbLevelGate"' in script
    assert "-level $native_level" in script
    assert "-level $level" in script
    assert "::npi_L1::npi_crdb_corr_sig" in script


@pytest.mark.contract
def test_archived_vm_responses_match_action_schemas(kdebug_root: Path) -> None:
    evidence = kdebug_root / "tests" / "vm" / "npi_actions" / "evidence"
    summary = json.loads((evidence / "vm-summary.json").read_text(encoding="utf-8"))
    assert summary["passed"] is True
    assert summary["unexpected_failures"] == []
    assert summary["license_blocked_actions"] == ["power.list", "power.resolve"]

    response_paths = sorted((evidence / "responses").glob("*.json"))
    assert len(response_paths) == 38
    for response_path in response_paths:
        response = json.loads(response_path.read_text(encoding="utf-8"))
        action = response["action"]
        schema_path = (
            kdebug_root / "schemas" / "v1" / "actions" / (action + ".response.schema.json")
        )
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator(schema).validate(response)


@pytest.mark.contract
def test_archived_vm_module_evidence_contains_elaborated_facts(
    kdebug_root: Path,
) -> None:
    responses = kdebug_root / "tests" / "vm" / "npi_actions" / "evidence" / "responses"

    instances = json.loads(
        (responses / "module.find_instances.json").read_text(encoding="utf-8")
    )["data"]["instances"]
    assert any(
        row["object"]["full_name"] == "npi_fixture_top.u_alu" for row in instances
    )

    parameters = json.loads(
        (responses / "module.objects.parameters.json").read_text(encoding="utf-8")
    )["data"]["items"]
    by_name = {row["object"]["name"]: row for row in parameters}
    assert by_name["WIDTH"]["values"]["dec"] == "12"
    assert by_name["BIAS"]["values"]["dec"] == "1"
    assert by_name["RESULT_WIDTH"]["object"]["local_param"] == 1
    assert by_name["RESULT_WIDTH"]["values"]["dec"] == "12"

    ports = json.loads(
        (responses / "module.objects.ports.json").read_text(encoding="utf-8")
    )["data"]["items"]
    directions = {row["object"]["name"]: row["object"]["direction"] for row in ports}
    assert directions == {"lhs": "npiInput", "rhs": "npiInput", "result": "npiOutput"}
    for row in ports:
        assert row["object"]["parent_module"] == "npi_fixture_top.u_alu"
        assert row["object"]["full_name"] == "npi_fixture_top.u_alu.%s" % row["object"]["name"]
        assert row["connections"]["high"]["full_name"]
        assert row["connections"]["low"]["full_name"]

    for kind in MODULE_OBJECT_KINDS:
        response = json.loads(
            (responses / ("module.objects.%s.json" % kind)).read_text(encoding="utf-8")
        )
        assert response["ok"] is True
        assert response["data"]["kind"] == kind
