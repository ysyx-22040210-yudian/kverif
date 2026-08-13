from __future__ import annotations

import errno
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


def _make_elab_dir(root: Path) -> Path:
    elab = root / "simv.daidir" / "kdb.elab++"
    elab.mkdir(parents=True)
    (elab / "design.db").write_text("fixture", encoding="utf-8")
    return elab


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
@pytest.mark.parametrize("signal_count", [2, 50000])
def test_string_batch_plan_is_hex_encoded_and_ordered(
    signal_count: int,
    kdebug_root: Path, tmp_path: Path
) -> None:
    engine = _load_engine(kdebug_root)
    signals = ["top.u_%05d.ready[0]" % index for index in range(signal_count)]
    path = engine.prepare_string_batch_plan(
        {"signals": signals},
        "signals",
        str(tmp_path),
        "signals.tsv",
    )
    rows = Path(path).read_text(encoding="utf-8").splitlines()
    assert [bytes.fromhex(row).decode("utf-8") for row in rows] == signals


@pytest.mark.contract
def test_value_batch_at_transports_50000_signals_by_plan_file(
    kdebug_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = _load_engine(kdebug_root)
    signals = ["top.u_%05d.ready[0]" % index for index in range(50000)]
    captured = {}

    class FakePopen:
        returncode = 0

        def __init__(self, command, **kwargs):
            self.env = kwargs["env"]
            captured["command"] = command

        def communicate(self, timeout=None):
            assert "KDEBUG_TCL_SIGNALS" not in self.env
            plan = Path(self.env["KDEBUG_TCL_SIGNAL_PLAN"])
            captured["signals"] = [
                bytes.fromhex(row).decode("utf-8")
                for row in plan.read_text(encoding="utf-8").splitlines()
            ]
            Path(self.env["KDEBUG_TCL_RESPONSE_JSON"]).write_text(
                json.dumps({"ok": True, "data": {"values": []}}),
                encoding="utf-8",
            )
            return "", ""

    monkeypatch.setattr(engine, "find_verdi", lambda: "/fake/verdi")
    monkeypatch.setattr(engine.subprocess, "Popen", FakePopen)
    ok, data = engine.run_tcl_npi(
        {
            "action": "value.batch_at",
            "target": {"fsdb": "/data/waves.fsdb"},
            "args": {"signals": signals, "time": "10ns"},
        },
        {"target": {}},
    )

    assert ok is True
    assert data["values"] == []
    assert captured["signals"] == signals
    assert sum(len(signal) for signal in signals) >= 1000000


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

    normalized = engine.prepare_port_trace_environment(
        {
            "module": "MSHR",
            "ports": [
                "io_id[0008]",
                "io_range[0009:0000]",
                "huge[09223372036854775808]",
            ],
        },
        {},
        {"daidir": "/data/build/simv.daidir"},
        str(tmp_path),
    )
    normalized_rows = Path(normalized["KDEBUG_TCL_PORT_PLAN"]).read_text(
        encoding="utf-8"
    ).splitlines()
    assert [bytes.fromhex(row).decode("utf-8") for row in normalized_rows] == [
        "io_id[8]",
        "io_range[9:0]",
        "huge[9223372036854775808]",
    ]

    with pytest.raises(ValueError, match="ports must not contain duplicates"):
        engine.prepare_port_trace_environment(
            {"module": "MSHR", "ports": ["io_id[8]", "io_id[08]"]},
            {},
            {"daidir": "/data/build/simv.daidir"},
            str(tmp_path),
        )

    with pytest.raises(ValueError, match="valid port or bit-select"):
        engine.prepare_port_trace_environment(
            {"module": "MSHR", "ports": ["io_id; exec bad"]},
            {},
            {"daidir": "/data/build/simv.daidir"},
            str(tmp_path),
        )


@pytest.mark.contract
def test_port_trace_environment_supports_large_stop_cut_sets(
    kdebug_root: Path, tmp_path: Path
) -> None:
    engine = _load_engine(kdebug_root)
    stops = ["top.cluster_%05d.u_stop" % index for index in range(5001)]
    env = engine.prepare_port_trace_environment(
        {"module": "MSHR", "stop_instances": stops},
        {},
        {"daidir": "/data/build/simv.daidir"},
        str(tmp_path),
    )
    rows = Path(env["KDEBUG_TCL_STOP_INSTANCE_PLAN"]).read_text(
        encoding="utf-8"
    ).splitlines()
    assert [bytes.fromhex(row).decode("utf-8") for row in rows] == stops

    schema = json.loads(
        (
            kdebug_root
            / "schemas"
            / "v1"
            / "actions"
            / "port.trace_batch.request.schema.json"
        ).read_text(encoding="utf-8")
    )
    args_schema = schema["properties"]["args"]["properties"]
    assert "maxItems" not in args_schema["stop_instances"]
    assert args_schema["stop_instances"]["uniqueItems"] is True
    assert "maxItems" not in args_schema["ports"]
    assert args_schema["ports"]["uniqueItems"] is True


@pytest.mark.contract
@pytest.mark.parametrize("port_count", [5001, 50000])
def test_port_trace_environment_supports_large_port_filters(
    kdebug_root: Path, tmp_path: Path, port_count: int
) -> None:
    engine = _load_engine(kdebug_root)
    ports = ["port_%05d" % index for index in range(port_count)]
    env = engine.prepare_port_trace_environment(
        {"module": "MSHR", "ports": ports},
        {},
        {"daidir": "/data/build/simv.daidir"},
        str(tmp_path),
    )
    rows = Path(env["KDEBUG_TCL_PORT_PLAN"]).read_text(
        encoding="utf-8"
    ).splitlines()
    assert [bytes.fromhex(row).decode("utf-8") for row in rows] == ports

    with pytest.raises(ValueError, match="ports must not contain duplicates"):
        engine.prepare_port_trace_environment(
            {"module": "MSHR", "ports": ["ready", "ready"]},
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
    assert calls[0].command[-2:] == [
        "-dbdir", engine.normalized_path("/data/build/simv.daidir")
    ]
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
def test_port_trace_tcl_hdl_decimal_text_never_uses_tcl_octal(
    kdebug_root: Path, tmp_path: Path
) -> None:
    tclsh = shutil.which("tclsh")
    if not tclsh:
        pytest.skip("tclsh is unavailable")
    wrapper = tmp_path / "port_trace_decimal_indices.tcl"
    wrapper.write_text(
        r"""
source {%s}
puts "decimal-09=[normalize_decimal_uint 09]"
puts "decimal-010=[normalize_decimal_uint 010]"
puts "decimal-zero=[normalize_decimal_uint 000]"
puts "invalid-decimal=[list [normalize_decimal_uint {}] [normalize_decimal_uint x] [normalize_decimal_uint -1]]"
puts "lhs-offset=[lhs_select_rhs_bit_for_target {[09:00]} 09]"
puts "invalid-lhs-offset=[lhs_select_rhs_bit_for_target {[09:00]} x]"
puts "rhs-offset=[lindex [rhs_item_offsets_for_signal_bit {a[09:00]} a 09] 0]"
set widths [parse_signal_width_text {logic [09:00] a;}]
puts "decl-width=[dict get $widths a]"
puts "expr-width=[expr_item_width {a[09:00]}]"
puts "select-bits=[join [select_selected_bits {[09:08]}] ,]"
puts "decimal-literal=[project_const_literal_to_bit {Const:010} 1]"
puts "invalid-literal-bit=[project_const_literal_to_bit {Const:09} x]"
puts "normalized-name=[normalize_signal_name {top.a[010]}]"
puts "trace-limits=[list [kdebug_port_trace_int 08 16] [kdebug_port_trace_int 09 16] [kdebug_port_trace_int 010 16] [kdebug_port_trace_int x 16]]"
puts "select-suffix=[bits_to_select_suffix {010 08 09 09}]"
puts "large-select-suffix=[bits_to_select_suffix {9223372036854775808 9223372036854775809}]"
puts "invalid-select-suffix=[bits_to_select_suffix {08 x}]"
"""
        % (kdebug_root / "tcl_engine" / "kdebug_port_trace.tcl").as_posix(),
        encoding="utf-8",
    )
    completed = subprocess.run(
        [tclsh, str(wrapper)], capture_output=True, text=True, timeout=20
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.splitlines() == [
        "decimal-09=9",
        "decimal-010=10",
        "decimal-zero=0",
        "invalid-decimal={} {} {}",
        "lhs-offset=9",
        "invalid-lhs-offset=",
        "rhs-offset=9",
        "decl-width=10",
        "expr-width=10",
        "select-bits=8,9",
        "decimal-literal=Const:1'b1",
        "invalid-literal-bit=",
        "normalized-name=top.a[10]",
        "trace-limits=8 9 10 16",
        "select-suffix=[10:8]",
        "large-select-suffix=[9223372036854775809:9223372036854775808]",
        "invalid-select-suffix=",
    ]


@pytest.mark.contract
def test_port_trace_tcl_depth_markers_require_observed_continuation(
    kdebug_root: Path, tmp_path: Path
) -> None:
    tclsh = shutil.which("tclsh")
    if not tclsh:
        pytest.skip("tclsh is unavailable")
    wrapper = tmp_path / "port_trace_depth_markers.tcl"
    wrapper.write_text(
        r"""
source {%s}
namespace eval ::npi_L1 {}
proc log_step {msg} {}
proc hdl_to_name {hdl args} {
    if {$hdl eq "ASSIGN"} {return top.assign_net}
    if {$hdl eq "EXPR"} {return expr_net}
    if {$hdl eq "DRIVER_EXPR"} {return expr_driver}
    if {$hdl eq "LOAD_ASSIGN"} {return top.load_net}
    if {$hdl eq "LOAD_NEXT"} {return top.load_next}
    if {$hdl eq "LEAF"} {return top.leaf}
    if {$hdl eq "NEXT"} {return top.next}
    return $hdl
}
proc hdl_evidence_name {hdl} {return "hdl:$hdl"}
proc hdl_kind {hdl} {
    if {$hdl eq "ASSIGN" || $hdl eq "NEXT"} {return net}
    if {$hdl eq "EXPR" || $hdl eq "DRIVER_EXPR"} {return expr}
    if {$hdl eq "LOAD_ASSIGN" || $hdl eq "LOAD_NEXT"} {return net}
    return pin
}
proc signal_belongs_to_stop_instance {name} {return 0}
proc exact_literal_handle_for_driver {hdl} {return ""}
proc raw_bit_driver_handles_by_hdl {hdl status_var count_var} {
    upvar 1 $status_var status $count_var count
    set status 1
    set count 0
    return {}
}
proc ::npi_L1::npi_nl_pass_assign_cell {hdl} {
    if {$hdl eq "ASSIGN"} {return NEXT}
    return ""
}
proc module_port_high_conn_pairs {hdl signame role args} {return {}}
proc scoped_signal_for_query {signame args} {return $signame}
proc collect_conn_module_ports_by_name {signame role all_var module_var} {}
proc ::npi_L1::npi_nl_trace_load {signame result_var args} {
    upvar 1 $result_var result
    if {$signame eq "expr_net"} {
        set result {NEXT}
    } elseif {$signame eq "top.load_net"} {
        set result {LOAD_NEXT}
    } else {
        set result {}
    }
}
proc ::npi_L1::npi_nl_trace_driver {signame result_var args} {
    upvar 1 $result_var result
    if {$signame eq "expr_driver"} {set result {NEXT}} else {set result {}}
}

set const_trace_max_depth 4
set assign_trace_max_depth 0
set assign_expr_trace_max_depth 0
reset_trace_depth_limit_markers
puts "leaf-decision=[trace_endpoint_expansion_decision driver LEAF top.leaf 0 0]"
puts "leaf-markers=[trace_depth_limit_markers_for_role driver]"
puts "assign-decision=[trace_endpoint_expansion_decision driver ASSIGN top.assign_net 0 0]"
puts "assign-repeat=[trace_endpoint_expansion_decision driver ASSIGN top.assign_net 0 0]"
puts "driver-expr-decision=[trace_endpoint_expansion_decision driver DRIVER_EXPR expr_driver 0 0]"
puts "load-assign-decision=[trace_endpoint_expansion_decision load LOAD_ASSIGN top.load_net 0 0]"
puts "expr-decision=[trace_endpoint_expansion_decision load EXPR expr_net 0 0]"
set all_drivers {top.other_branch}
set module_drivers {}
append_trace_depth_limit_markers driver all_drivers module_drivers
puts "driver=$all_drivers|boundary=$module_drivers"
puts "load=[trace_depth_limit_markers_for_role load]"
set kdebug_port_trace_max_rows 0
set kdebug_port_trace_full_rows {}
set kdebug_port_trace_boundary_rows {}
set kdebug_port_trace_truncated 0
set kdebug_port_trace_row_limit_surfaces [dict create]
foreach marker $all_drivers {
    write_trace_row __KDEBUG_FULL__ top.u_dut a input driver $marker
}
foreach marker $module_drivers {
    write_trace_row __KDEBUG_BOUNDARY__ top.u_dut a input driver $marker
}
puts "rows=[dict get [lindex $kdebug_port_trace_full_rows end] signal_full_name]|boundary-row=[dict get [lindex $kdebug_port_trace_boundary_rows end] signal_full_name]|truncated=$kdebug_port_trace_truncated"

reset_trace_depth_limit_markers
set visited {}
puts "exact-leaf=[expand_exact_assign_driver_handle LEAF 0 visited]"
puts "exact-leaf-markers=[trace_depth_limit_markers_for_role driver]"
set visited {}
puts "exact-chain=[expand_exact_assign_driver_handle ASSIGN 0 visited]"
puts "exact-chain-markers=[trace_depth_limit_markers_for_role driver]"
"""
        % (kdebug_root / "tcl_engine" / "kdebug_port_trace.tcl").as_posix(),
        encoding="utf-8",
    )
    completed = subprocess.run(
        [tclsh, str(wrapper)], capture_output=True, text=True, timeout=20
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.splitlines() == [
        "leaf-decision=",
        "leaf-markers=",
        "assign-decision=",
        "assign-repeat=",
        "driver-expr-decision=",
        "load-assign-decision=",
        "expr-decision=",
        "driver=top.other_branch TRACE_LIMIT_REACHED:assign_depth_0 TRACE_LIMIT_REACHED:expr_depth_0|boundary=TRACE_LIMIT_REACHED:assign_depth_0 TRACE_LIMIT_REACHED:expr_depth_0",
        "load=TRACE_LIMIT_REACHED:assign_depth_0 TRACE_LIMIT_REACHED:expr_depth_0",
        "rows=TRACE_LIMIT_REACHED:expr_depth_0|boundary-row=TRACE_LIMIT_REACHED:expr_depth_0|truncated=1",
        "exact-leaf=LEAF",
        "exact-leaf-markers=",
        "exact-chain=ASSIGN",
        "exact-chain-markers=TRACE_LIMIT_REACHED:assign_depth_0",
    ]


@pytest.mark.contract
def test_port_trace_tcl_parent_depth_marker_distinguishes_leaf_and_loop(
    kdebug_root: Path, tmp_path: Path
) -> None:
    tclsh = shutil.which("tclsh")
    if not tclsh:
        pytest.skip("tclsh is unavailable")
    wrapper = tmp_path / "port_trace_parent_depth_marker.tcl"
    wrapper.write_text(
        r"""
source {%s}
proc log_step {msg} {}
proc log_const_source_detail {args} {}
proc qualify_signal_for_log {name args} {return $name}
proc get_inst_port_handle_by_signal {inst sig} {
    if {$inst eq "top.u"} {return START}
    if {$inst eq "top" && $sig eq "top.next"} {return NEXT}
    if {$inst eq "top" && $sig eq "top.loop"} {return LOOP}
    return ""
}
proc get_port_name {hdl} {return p_$hdl}
proc get_high_conn_sigs_for_port_hdl {inst hdl} {
    if {$hdl eq "START" && $::case_name eq "chain"} {return {H_NEXT}}
    if {$hdl eq "START" && $::case_name eq "leaf"} {return {H_LEAF}}
    if {$hdl eq "START" && $::case_name eq "loop"} {return {H_LOOP}}
    if {$hdl eq "NEXT"} {return {H_CONST}}
    if {$hdl eq "LOOP"} {return {H_LOOP}}
    return {}
}
proc hdl_to_selected_name {hdl args} {
    if {$hdl eq "H_NEXT"} {return top.next}
    if {$hdl eq "H_LEAF"} {return top.no_port}
    if {$hdl eq "H_LOOP"} {return top.loop}
    if {$hdl eq "H_CONST"} {return "1'b1"}
    return ""
}
proc select_hdl_for_signal_select {hdl select} {return $hdl}
proc parent_instance_path {inst} {
    if {$inst eq "top.u"} {return top}
    return ""
}
proc hdl_evidence_name {hdl} {return "hdl:$hdl"}
proc hdl_kind {hdl} {return net}

set const_trace_max_depth 1
set assign_trace_max_depth 2
set assign_expr_trace_max_depth 1
foreach case_name {chain leaf loop} {
    reset_trace_depth_limit_markers
    const_driver_from_parent_ports START top.u.start top.u 1
    puts "$case_name=[trace_depth_limit_markers_for_role driver]"
}
set const_trace_max_depth 0
reset_trace_depth_limit_markers
set case_name chain
const_driver_from_parent_ports START top.u.start top.u 0
puts "disabled-but-proven=[trace_depth_limit_markers_for_role driver]"
reset_trace_depth_limit_markers
set case_name leaf
const_driver_from_parent_ports START top.u.start top.u 0
puts "disabled-leaf=[trace_depth_limit_markers_for_role driver]"
"""
        % (kdebug_root / "tcl_engine" / "kdebug_port_trace.tcl").as_posix(),
        encoding="utf-8",
    )
    completed = subprocess.run(
        [tclsh, str(wrapper)], capture_output=True, text=True, timeout=20
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.splitlines() == [
        "chain=TRACE_LIMIT_REACHED:parent_depth_1",
        "leaf=",
        "loop=",
        "disabled-but-proven=TRACE_LIMIT_REACHED:parent_depth_0",
        "disabled-leaf=TRACE_LIMIT_REACHED:parent_depth_0",
    ]


@pytest.mark.contract
def test_port_trace_tcl_source_expr_depth_marker_distinguishes_direct_and_leaf(
    kdebug_root: Path, tmp_path: Path
) -> None:
    tclsh = shutil.which("tclsh")
    if not tclsh:
        pytest.skip("tclsh is unavailable")
    wrapper = tmp_path / "port_trace_source_expr_depth_marker.tcl"
    wrapper.write_text(
        r"""
source {%s}
proc log_step {msg} {}
proc source_assign_driver_sources_core {hdl signame srcfile include_expr args} {
    if {!$include_expr} {
        if {$signame eq "top.direct"} {return {top.direct_next}}
        return {}
    }
    if {$signame eq "top.chain"} {return {top.expr_next}}
    if {$signame eq "top.direct"} {return {top.direct_next}}
    if {$signame eq "top.const_chain"} {return {top.const_mid}}
    if {$signame eq "top.const_mid"} {return {{1'b1}}}
    return {}
}
proc source_assign_load_fanouts_core {hdl signame include_expr srcfile args} {
    if {!$include_expr} {
        if {$signame eq "top.direct"} {return {top.direct_next}}
        return {}
    }
    if {$signame eq "top.chain"} {return {top.expr_next}}
    if {$signame eq "top.direct"} {return {top.direct_next}}
    return {}
}
proc signal_scope_hint_after {signame args} {return ""}
proc log_const_sources_for_signal {args} {}

set const_trace_max_depth 4
set assign_trace_max_depth 2
set assign_expr_trace_max_depth 0
foreach signame {top.chain top.direct top.leaf} {
    reset_trace_depth_limit_markers
    source_assign_driver_sources "" $signame dummy.sv ""
    source_assign_load_fanouts "" $signame dummy.sv ""
    puts "$signame|driver=[trace_depth_limit_markers_for_role driver]|load=[trace_depth_limit_markers_for_role load]"
}

set assign_expr_trace_max_depth 1
reset_trace_depth_limit_markers
set visited {}
puts "const-depth1=[source_assign_const_chain top.const_chain dummy.sv 1 visited]"
puts "const-marker=[trace_depth_limit_markers_for_role driver]"
reset_trace_depth_limit_markers
set visited {}
puts "leaf-depth1=[source_assign_const_chain top.leaf dummy.sv 1 visited]"
puts "leaf-marker=[trace_depth_limit_markers_for_role driver]"
"""
        % (kdebug_root / "tcl_engine" / "kdebug_port_trace.tcl").as_posix(),
        encoding="utf-8",
    )
    completed = subprocess.run(
        [tclsh, str(wrapper)], capture_output=True, text=True, timeout=20
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.splitlines() == [
        "top.chain|driver=TRACE_LIMIT_REACHED:expr_depth_0|load=TRACE_LIMIT_REACHED:expr_depth_0",
        "top.direct|driver=|load=",
        "top.leaf|driver=|load=",
        "const-depth1=",
        "const-marker=TRACE_LIMIT_REACHED:expr_depth_1",
        "leaf-depth1=",
        "leaf-marker=",
    ]


@pytest.mark.contract
def test_port_trace_tcl_indexes_large_stop_cut_sets(
    kdebug_root: Path, tmp_path: Path
) -> None:
    tclsh = shutil.which("tclsh")
    if not tclsh:
        pytest.skip("tclsh is unavailable")
    wrapper = tmp_path / "port_trace_large_stops.tcl"
    wrapper.write_text(
        """
source {%s}

proc assert_stop_match {label expected signal_name} {
    set actual [signal_belongs_to_stop_instance $signal_name]
    if {$actual != $expected} {
        puts stderr "FAILED $label signal={$signal_name} expected=$expected actual=$actual"
        exit 2
    }
}

set stops {}
for {set index 0} {$index < 50000} {incr index} {
    lappend stops "Top.tile${index}.u_stop"
}
configure_load_trace_stop_instances $stops
if {[dict size $load_trace_stop_instance_set] != 50000} {
    puts stderr "FAILED configured stop count"
    exit 2
}

set current_trace_instance Top.tile7.u_stop
assert_stop_match exact 1 Top.tile0.u_stop
assert_stop_match exact_last 1 Top.tile49999.u_stop
assert_stop_match direct 1 Top.tile0.u_stop.out
assert_stop_match direct_child_port 1 Top.tile0.u_stop.child.out
assert_stop_match deep 0 Top.tile0.u_stop.child.deep.out
assert_stop_match slash 1 Top.tile0.u_stop/net/deep
assert_stop_match current_exact 0 Top.tile7.u_stop
assert_stop_match current_direct 0 Top.tile7.u_stop.out
assert_stop_match current_deep 0 Top.tile7.u_stop.child.out
assert_stop_match bit_select 1 {Top.tile0.u_stop.out[3]}
assert_stop_match missing 0 Top.missing.u_stop.out
assert_stop_match constant 0 {Const:1'b0}

set started [clock milliseconds]
for {set index 0} {$index < 2000} {incr index} {
    if {[signal_belongs_to_stop_instance "Top.missing${index}.net"]} {
        puts stderr "FAILED scaled miss query index=$index"
        exit 2
    }
}
puts "OK stops=50000 misses=2000 elapsed_ms=[expr {[clock milliseconds] - $started}]"
"""
        % (kdebug_root / "tcl_engine" / "kdebug_port_trace.tcl").as_posix(),
        encoding="utf-8",
    )
    completed = subprocess.run(
        [tclsh, str(wrapper)], capture_output=True, text=True, timeout=60
    )
    assert completed.returncode == 0, completed.stderr
    assert "OK stops=50000 misses=2000" in completed.stdout


@pytest.mark.contract
def test_port_trace_tcl_indexes_large_port_filters(
    kdebug_root: Path, tmp_path: Path
) -> None:
    tclsh = shutil.which("tclsh")
    if not tclsh:
        pytest.skip("tclsh is unavailable")
    wrapper = tmp_path / "port_trace_large_ports.tcl"
    wrapper.write_text(
        """
source {%s}

set ports {}
for {set index 0} {$index < 50000} {incr index} {
    lappend ports "port_${index}"
}
configure_port_trace_ports $ports
if {[dict size $port_filter_set] != 50000} {
    puts stderr "FAILED configured port count"
    exit 2
}
if {![port_trace_port_selected port_0] ||
    ![port_trace_port_selected port_49999] ||
    [port_trace_port_selected port_missing]} {
    puts stderr "FAILED indexed port membership"
    exit 2
}

set started [clock milliseconds]
for {set index 0} {$index < 2000} {incr index} {
    if {![port_trace_port_selected "port_${index}"] ||
        [port_trace_port_selected "missing_${index}"]} {
        puts stderr "FAILED scaled port query index=$index"
        exit 2
    }
}
set elapsed [expr {[clock milliseconds] - $started}]
if {$elapsed > 5000} {
    puts stderr "FAILED indexed port queries elapsed_ms=$elapsed"
    exit 2
}

configure_port_trace_ports {wide[0] wide[7:4] plain}
set selected_wide [selected_port_names wide]
if {[llength $selected_wide] != 2 ||
    [lsearch -exact $selected_wide {wide[0]}] < 0 ||
    [lsearch -exact $selected_wide {wide[7:4]}] < 0} {
    puts stderr "FAILED bit/range select map: $selected_wide"
    exit 2
}
if {![port_trace_port_selected wide] || ![port_trace_port_selected plain]} {
    puts stderr "FAILED selected base ports"
    exit 2
}

configure_port_trace_ports {}
if {[dict size $port_filter_set] != 0 ||
    [dict size $port_filter_select_map] != 0 ||
    ![port_trace_port_selected any_design_port]} {
    puts stderr "FAILED empty filter must select all ports"
    exit 2
}
puts "OK ports=50000 hits=2000 misses=2000 elapsed_ms=$elapsed empty=all"
"""
        % (kdebug_root / "tcl_engine" / "kdebug_port_trace.tcl").as_posix(),
        encoding="utf-8",
    )
    completed = subprocess.run(
        [tclsh, str(wrapper)], capture_output=True, text=True, timeout=60
    )
    assert completed.returncode == 0, completed.stderr
    assert "OK ports=50000 hits=2000 misses=2000" in completed.stdout
    assert "empty=all" in completed.stdout


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
            return [list 1 "" "" 1 0 0]
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
def test_port_trace_tcl_wrapper_preserves_all_failed_instance_details(
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
    port_plan.write_bytes(("%s\n" % "a[08]".encode("utf-8").hex()).encode("ascii"))
    stop_plan.write_bytes(b"")
    wrapper = tmp_path / "port_trace_all_failed_stub.tcl"
    npi_script = (kdebug_root / "tcl_engine" / "kdebug_npi.tcl").as_posix()
    wrapper.write_text(
        r'''
rename source __real_source
proc source {path} {
    if {[string match *npi_L1.tcl $path]} {return}
    if {[file tail $path] eq "kdebug_port_trace.tcl"} {
        uplevel 1 [list __real_source $path]
        rename kdebug_port_trace_run kdebug_port_trace_run_legacy
        proc kdebug_port_trace_run {module ports stops source fallback full boundary args} {
            set ::kdebug_port_trace_errors [list \
                [dict create scope instance code INSTANCE_TRACE_FAILED message {can't use invalid octal number as operand of "-"} instance top.u0] \
                [dict create scope instance code INSTANCE_TRACE_FAILED message {second original failure} instance top.u1]]
            return [list 0 TRACE_FAILED {all instances failed} 0 1 2]
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
set env(KDEBUG_TCL_INCLUDE_BOUNDARY) 0
set env(KDEBUG_TCL_MAX_PARENT_DEPTH) 16
set env(KDEBUG_TCL_MAX_ASSIGN_DEPTH) 2
set env(KDEBUG_TCL_MAX_EXPR_DEPTH) 1
set env(KDEBUG_TCL_MAX_NODES) 20000
set env(KDEBUG_TCL_MAX_EDGES) 100000
set env(KDEBUG_TCL_MAX_API_RESULTS) 20000
set env(KDEBUG_TCL_MAX_ROWS) 20000
__real_source {%s}
'''
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
    assert payload["ok"] is False
    assert payload["error"]["code"] == "TRACE_FAILED"
    details = payload["error"]["details"]
    assert details["module"] == "Dut"
    assert details["requested_ports"] == ["a[08]"]
    assert details["stats"] == {
        "processed_instances": 0,
        "failed_instances": 2,
        "skipped_instances": 1,
        "error_count": 2,
    }
    assert [item["instance"] for item in details["errors"]] == ["top.u0", "top.u1"]
    assert "invalid octal number" in details["errors"][0]["message"]


@pytest.mark.contract
def test_port_trace_tcl_wrapper_preserves_all_skipped_instance_details(
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
    wrapper = tmp_path / "port_trace_all_skipped_stub.tcl"
    npi_script = (kdebug_root / "tcl_engine" / "kdebug_npi.tcl").as_posix()
    wrapper.write_text(
        r'''
rename source __real_source
proc source {path} {
    if {[string match *npi_L1.tcl $path]} {return}
    if {[file tail $path] eq "kdebug_port_trace.tcl"} {
        uplevel 1 [list __real_source $path]
        rename kdebug_port_trace_run kdebug_port_trace_run_legacy
        proc kdebug_port_trace_run args {
            set ::kdebug_port_trace_errors [list [dict create \
                scope instance code INSTANCE_PATH_UNAVAILABLE \
                message {could not resolve an instance path} handle HDL_1]]
            return [list 0 TRACE_FAILED \
                {port trace produced no successful instances; inspect instance_errors} 0 1 0]
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
'''
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
    assert payload["ok"] is False
    assert payload["error"]["code"] == "TRACE_FAILED"
    details = payload["error"]["details"]
    assert details["module"] == "Dut"
    assert details["errors"] == [
        {
            "scope": "instance",
            "code": "INSTANCE_PATH_UNAVAILABLE",
            "message": "could not resolve an instance path",
            "handle": "HDL_1",
        }
    ]
    assert details["stats"] == {
        "processed_instances": 0,
        "failed_instances": 0,
        "skipped_instances": 1,
        "error_count": 1,
    }


@pytest.mark.contract
def test_port_trace_run_rejects_all_unresolved_instance_paths(
    kdebug_root: Path, tmp_path: Path
) -> None:
    tclsh = shutil.which("tclsh")
    if not tclsh:
        pytest.skip("tclsh is unavailable")
    wrapper = tmp_path / "port_trace_all_paths_unresolved.tcl"
    trace_script = (kdebug_root / "tcl_engine" / "kdebug_port_trace.tcl").as_posix()
    wrapper.write_text(
        r'''
source {%s}
namespace eval ::npi_L1 {}
proc ::npi_L1::npi_find_inst_with_def_wildcard {scope module output_name} {
    upvar 1 $output_name handles
    set handles {fake_handle}
}
proc get_instance_path {handle} {return {}}
proc npi_release_handle args {return}
lassign [kdebug_port_trace_run Dut {a} {} {} 1 1 1 16 2 1 20000 100000 20000 20000 0] \
    succeeded code message processed skipped failed
if {$succeeded || $code ne "TRACE_FAILED" || $processed != 0 || \
    $skipped != 1 || $failed != 0} {
    puts stderr "unexpected result: $succeeded $code $processed $skipped $failed"
    exit 2
}
if {[llength $::kdebug_port_trace_errors] != 1} {
    puts stderr "expected one instance path error"
    exit 2
}
set error_record [lindex $::kdebug_port_trace_errors 0]
if {[dict get $error_record code] ne "INSTANCE_PATH_UNAVAILABLE" || \
    [dict get $error_record handle] ne "fake_handle"} {
    puts stderr "instance path evidence is incomplete: $error_record"
    exit 2
}
puts OK
'''
        % trace_script,
        encoding="utf-8",
    )
    completed = subprocess.run(
        [tclsh, str(wrapper)], capture_output=True, text=True, timeout=20
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "OK"


@pytest.mark.contract
def test_port_trace_instance_failure_with_boundary_disabled_does_not_write_empty_channel(
    kdebug_root: Path, tmp_path: Path
) -> None:
    tclsh = shutil.which("tclsh")
    if not tclsh:
        pytest.skip("tclsh is unavailable")
    wrapper = tmp_path / "port_trace_no_boundary.tcl"
    trace_script = (kdebug_root / "tcl_engine" / "kdebug_port_trace.tcl").as_posix()
    wrapper.write_text(
        r'''
source {%s}
namespace eval ::npi_L1 {}
proc ::npi_L1::npi_find_inst_with_def_wildcard {scope module output_name} {
    upvar 1 $output_name handles
    set handles {fake_handle}
}
proc get_instance_path {handle} {return top.u_bad}
proc process_instance args {error {synthetic instance failure}}
proc npi_release_handle args {return}
lassign [kdebug_port_trace_run Dut {a} {} {} 1 1 0 16 2 1 20000 100000 20000 20000 0] \
    succeeded code message processed skipped failed
if {$succeeded || $code ne "TRACE_FAILED" || $processed != 0 || $failed != 1} {
    puts stderr "unexpected result: $succeeded $code $processed $skipped $failed"
    exit 2
}
if {[llength $::kdebug_port_trace_boundary_rows] != 0} {
    puts stderr "boundary rows should remain empty"
    exit 2
}
puts OK
'''
        % trace_script,
        encoding="utf-8",
    )
    completed = subprocess.run(
        [tclsh, str(wrapper)], capture_output=True, text=True, timeout=20
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "OK"


@pytest.mark.contract
def test_port_trace_rolls_back_failed_instance_and_keeps_successful_instance(
    kdebug_root: Path, tmp_path: Path
) -> None:
    tclsh = shutil.which("tclsh")
    if not tclsh:
        pytest.skip("tclsh is unavailable")
    wrapper = tmp_path / "port_trace_partial_failure.tcl"
    trace_script = (kdebug_root / "tcl_engine" / "kdebug_port_trace.tcl").as_posix()
    wrapper.write_text(
        r'''
source {%s}
namespace eval ::npi_L1 {}
proc ::npi_L1::npi_find_inst_with_def_wildcard {scope module output_name} {
    upvar 1 $output_name handles
    set handles {good_handle bad_handle}
}
proc get_instance_path {handle} {
    if {$handle eq "good_handle"} {return top.u_good}
    return top.u_bad
}
proc npi_release_handle args {return}
proc process_instance {inst_path parent_path instname full_fh boundary_fh} {
    set full_row [dict create inst_full_name $inst_path port_name a port_dir input role driver signal_full_name "${inst_path}.source"]
    set boundary_row [dict create inst_full_name $inst_path port_name a port_dir input role driver signal_full_name "${inst_path}.boundary"]
    lappend ::kdebug_port_trace_full_rows $full_row
    lappend ::kdebug_port_trace_boundary_rows $boundary_row
    lappend ::kdebug_port_trace_evidence [dict create \
        method source_port_connection value Const:1'b1 \
        const_full_path "${inst_path}.a<-Const:1'b1" fields {}]
    dict set ::kdebug_port_trace_seen_ports "${inst_path}|a" 1
    if {$inst_path eq "top.u_bad"} {
        set ::kdebug_port_trace_truncated 1
        error {can't use invalid octal number as operand of "-"}
    }
}
lassign [kdebug_port_trace_run Dut {a} {} {} 1 1 1 16 2 1 20000 100000 20000 20000 0] \
    succeeded code message processed skipped failed
if {!$succeeded || $processed != 1 || $failed != 1 || $skipped != 0} {
    puts stderr "unexpected result: $succeeded $code $processed $skipped $failed"
    exit 2
}
if {[llength $::kdebug_port_trace_evidence] != 1 || \
    [dict get [lindex $::kdebug_port_trace_evidence 0] const_full_path] ne "top.u_good.a<-Const:1'b1"} {
    puts stderr "failed instance evidence was not rolled back"
    exit 2
}
if {[dict exists $::kdebug_port_trace_seen_ports "top.u_bad|a"] || \
    ![dict exists $::kdebug_port_trace_seen_ports "top.u_good|a"]} {
    puts stderr "failed instance seen-port state was not rolled back"
    exit 2
}
if {$::kdebug_port_trace_truncated} {
    puts stderr "failed instance truncation state was not rolled back"
    exit 2
}
foreach rows [list $::kdebug_port_trace_full_rows $::kdebug_port_trace_boundary_rows] {
    if {[llength $rows] != 3} {
        puts stderr "expected one success row and two failure markers"
        exit 2
    }
    set signals {}
    foreach row $rows {lappend signals [dict get $row signal_full_name]}
    if {[lsearch -exact $signals top.u_bad.source] >= 0 || \
        [lsearch -exact $signals top.u_bad.boundary] >= 0} {
        puts stderr "failed instance partial row survived rollback"
        exit 2
    }
    if {[llength [lsearch -all -exact $signals ERROR:INSTANCE_TRACE_FAILED]] != 2} {
        puts stderr "failure markers are incomplete"
        exit 2
    }
}
if {[llength $::kdebug_port_trace_errors] != 1 || \
    [dict get [lindex $::kdebug_port_trace_errors 0] instance] ne "top.u_bad"} {
    puts stderr "instance error evidence is missing"
    exit 2
}
puts OK
'''
        % trace_script,
        encoding="utf-8",
    )
    completed = subprocess.run(
        [tclsh, str(wrapper)], capture_output=True, text=True, timeout=20
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "OK"


@pytest.mark.contract
def test_tcl_failure_details_survive_public_and_session_responses(
    kdebug_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = _load_engine(kdebug_root)
    details = {
        "module": "Dut",
        "errors": [{
            "scope": "instance",
            "code": "INSTANCE_TRACE_FAILED",
            "message": "original trace failure",
            "instance": "top.u0",
        }],
        "stats": {
            "processed_instances": 0,
            "failed_instances": 1,
            "skipped_instances": 0,
            "error_count": 1,
        },
    }

    class FakePopen:
        returncode = 0

        def __init__(self, command, **kwargs):
            self.env = kwargs["env"]

        def communicate(self, timeout=None):
            Path(self.env["KDEBUG_TCL_RESPONSE_JSON"]).write_text(
                json.dumps({
                    "ok": False,
                    "error": {
                        "code": "TRACE_FAILED",
                        "message": "all instances failed",
                        "details": details,
                    },
                }),
                encoding="utf-8",
            )
            return "", "verdi diagnostic"

    monkeypatch.setattr(engine, "resolve_design_database", lambda target: {
        "kind": "daidir", "path": "/data/build/simv.daidir"
    })
    monkeypatch.setattr(engine, "find_verdi", lambda: "/fake/verdi")
    monkeypatch.setattr(engine.subprocess, "Popen", FakePopen)
    ok, error = engine.run_tcl_npi(
        {
            "action": "port.trace_batch",
            "target": {"daidir": "/data/build/simv.daidir"},
            "args": {"module": "Dut", "ports": ["a"]},
        },
        {"target": {}},
    )
    assert ok is False
    assert error["errors"] == details["errors"]
    assert error["stats"] == details["stats"]
    public = engine.wrap_public_action_response(
        {"action": "port.trace_batch"}, False, error
    )
    assert public["error"]["details"]["errors"] == details["errors"]

    monkeypatch.setattr(engine.Registry, "get", lambda self, session_id: {
        "session_id": session_id,
        "mode": "design",
        "transport": "uds",
    })
    monkeypatch.setattr(engine, "route_to_session", lambda record, request: {
        "ok": False,
        "error": {"code": "TRACE_FAILED", "message": "all instances failed"},
        "details": error,
    })
    session_public = engine.one_shot_engine_action({
        "action": "port.trace_batch",
        "target": {"session_id": "trace_session"},
    })
    assert session_public["error"]["details"]["errors"] == details["errors"]
    assert session_public["error"]["details"]["stats"] == details["stats"]


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
def test_module_find_instances_round_trips_into_inspect_when_language_lookup_misses(
    kdebug_root: Path, tmp_path: Path
) -> None:
    tclsh = shutil.which("tclsh")
    if not tclsh:
        pytest.skip("tclsh is unavailable")

    parent = "tb_top.sim.cpu.l_soc.core_with_l2.l2top.inner_l2cache.slices_0.mshrCtl"
    valid_with_parameter = f"{parent}.mshrs_8"
    valid_without_parameter = f"{parent}.mshrs_9"
    missing = f"{parent}.mshrs_10"
    npi_dir = tmp_path / "npi"
    npi_dir.mkdir()
    (npi_dir / "npi_L1.tcl").write_text(
        r'''
namespace eval ::npi_L1 {}
set ::fixture_parent {%s}
set ::fixture_paths [list {%s} {%s}]

proc ::npi_L1::npi_mod_define_get_inst {definition output_name} {
    upvar 1 $output_name handles
    if {$definition eq "MSHR"} {
        set handles {INST8 INST9}
        return 2
    }
    set handles {}
    return 0
}

proc ::npi_L1::npi_mod_inst_get_parameter {module output_name} {
    upvar 1 $output_name handles
    if {$module eq [lindex $::fixture_paths 0]} {
        set handles {PARAM}
        return 1
    }
    set handles {}
    return 0
}

proc ::npi_L1::npi_mod_inst_get_instance {module output_name} {
    upvar 1 $output_name handles
    if {$module eq $::fixture_parent} {
        set handles {INST8 INST9}
        return 2
    }
    set handles {}
    return 0
}

proc ::npi_L1::npi_mod_inst_get_instance_in_gen_scope {module output_name} {
    upvar 1 $output_name handles
    set handles {}
    return 0
}

proc npi_handle_by_name args {
    # Reproduce the elab++ false negative for generated numeric hierarchy names.
    return ""
}

proc npi_get_str args {
    array set option $args
    set hdl $option(-object)
    set property $option(-property)
    if {$hdl eq "INST8"} {set full_name [lindex $::fixture_paths 0]}
    if {$hdl eq "INST9"} {set full_name [lindex $::fixture_paths 1]}
    if {$hdl eq "PARAM"} {set full_name "[lindex $::fixture_paths 0].SETS"}
    switch -- $property {
        npiFullName {return $full_name}
        npiName {
            if {$hdl eq "INST8"} {return mshrs_8}
            if {$hdl eq "INST9"} {return mshrs_9}
            if {$hdl eq "PARAM"} {return SETS}
        }
        npiType {
            if {$hdl eq "PARAM"} {return npiParameter}
            return npiModule
        }
        npiDefName {
            if {$hdl ne "PARAM"} {return MSHR}
        }
        npiConstType {
            if {$hdl eq "PARAM"} {return npiDecConst}
        }
    }
    return ""
}

proc npi_get args {
    array set option $args
    if {$option(-object) eq "PARAM" && $option(-property) eq "npiSize"} {return 32}
    return ""
}

proc npi_get_value args {
    array set option $args
    if {$option(-object) eq "PARAM"} {return 16}
    return NPI_GET_VALUE_ERROR_STR
}

proc npi_release_handle args {return}
''' % (parent, valid_with_parameter, valid_without_parameter),
        encoding="utf-8",
    )
    wrapper = tmp_path / "module_round_trip.tcl"
    wrapper.write_text(
        "proc debExit {} {return}\nsource {%s}\n"
        % (kdebug_root / "tcl_engine" / "kdebug_npi.tcl").as_posix(),
        encoding="utf-8",
    )

    def run_action(action: str, response: Path, **env_values: str) -> dict:
        env = os.environ.copy()
        env.update(
            {
                "NPIL1_PATH": str(npi_dir),
                "KDEBUG_TCL_ACTION": action,
                "KDEBUG_TCL_RESPONSE_JSON": str(response),
                "KDEBUG_TCL_MAX_ROWS": "20",
            }
        )
        env.update(env_values)
        completed = subprocess.run(
            [tclsh, str(wrapper)],
            capture_output=True,
            text=True,
            timeout=20,
            env=env,
        )
        assert completed.returncode == 0, completed.stderr
        return json.loads(response.read_text(encoding="utf-8"))

    find_response = run_action(
        "module.find_instances",
        tmp_path / "find.json",
        KDEBUG_TCL_DEFINITION="MSHR",
    )
    found_paths = [
        item["object"]["full_name"] for item in find_response["data"]["instances"]
    ]
    assert found_paths == [valid_with_parameter, valid_without_parameter]

    plan = tmp_path / "inspect.tsv"
    plan.write_bytes(
        "\n".join(path.encode("utf-8").hex() for path in [*found_paths, missing])
        .encode("ascii")
        + b"\n",
    )
    inspect_response = run_action(
        "module.inspect_batch",
        tmp_path / "inspect.json",
        KDEBUG_TCL_BATCH_PLAN=str(plan),
        KDEBUG_TCL_SECTIONS="parameters",
    )
    inspections = inspect_response["data"]["inspections"]
    assert [(item["module"], item["ok"]) for item in inspections] == [
        (valid_with_parameter, True),
        (valid_without_parameter, True),
        (missing, False),
    ]
    assert inspections[0]["data"]["counts"] == {"parameters": 1}
    assert inspections[1]["data"]["counts"] == {"parameters": 0}
    assert (
        inspections[1]["data"]["module_object"]["object"]["full_name"]
        == valid_without_parameter
    )
    assert inspections[2]["error"]["code"] == "MODULE_NOT_FOUND"
    assert inspect_response["data"]["summary"] == {
        "module_count": 3,
        "success_count": 2,
        "error_count": 1,
        "truncated": False,
    }

    missing_response = run_action(
        "module.inspect",
        tmp_path / "inspect_missing.json",
        KDEBUG_TCL_MODULE=missing,
        KDEBUG_TCL_SECTIONS="parameters",
    )
    assert missing_response["ok"] is False
    assert missing_response["error"]["code"] == "MODULE_NOT_FOUND"
    assert missing in missing_response["error"]["message"]


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
def test_vcs_summary_preserves_database_precedence_with_filelist_and_override(
    kdebug_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = _load_engine(kdebug_root)
    daidir = tmp_path / "simv.daidir"
    daidir.mkdir()
    filelist = tmp_path / "run.f"
    filelist.write_text("design.sv\n", encoding="utf-8")
    override = tmp_path / "override.daidir"
    override.mkdir()
    captured = []

    class FakePopen:
        returncode = 0

        def __init__(self, command, **kwargs):
            self.env = kwargs["env"]
            captured.append({"command": command, "env": self.env})

        def communicate(self, timeout=None):
            Path(self.env["KDEBUG_TCL_RESPONSE_JSON"]).write_text(
                json.dumps({"ok": True, "data": {"summary": {}}}), encoding="utf-8"
            )
            return "", ""

        def kill(self):
            return None

    monkeypatch.setattr(engine, "find_verdi", lambda: "/fake/verdi")
    monkeypatch.setattr(engine.subprocess, "Popen", FakePopen)

    ok, _ = engine.run_tcl_npi(
        {
            "action": "vcs.summary",
            "target": {"daidir": str(daidir), "filelist": str(filelist)},
            "args": {},
        },
        {"target": {}},
    )
    assert ok is True
    assert captured[-1]["env"]["KDEBUG_TCL_DATABASE"] == str(daidir)

    ok, _ = engine.run_tcl_npi(
        {
            "action": "vcs.summary",
            "target": {"daidir": str(tmp_path / "missing.elab++")},
            "args": {"database": str(override)},
        },
        {"target": {}},
    )
    assert ok is True
    assert captured[-1]["env"]["KDEBUG_TCL_DATABASE"] == str(override)

    elab = _make_elab_dir(tmp_path / "elab_target")
    ok, _ = engine.run_tcl_npi(
        {
            "action": "vcs.summary",
            "target": {"daidir": str(elab)},
            "args": {},
        },
        {"target": {}},
    )
    assert ok is True
    assert "-dbdir" not in captured[-1]["command"]
    assert "-ssf" not in captured[-1]["command"]
    assert "KDEBUG_TCL_ELAB" not in captured[-1]["env"]
    assert captured[-1]["env"]["KDEBUG_TCL_DATABASE"] == str(elab.parent)


@pytest.mark.contract
def test_elab_target_uses_native_import_instead_of_dbdir(
    kdebug_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = _load_engine(kdebug_root)
    elab = _make_elab_dir(tmp_path)
    fsdb = tmp_path / "waves.fsdb"
    captured = {}

    class FakePopen:
        returncode = 0

        def __init__(self, command, **kwargs):
            captured["command"] = command
            captured["env"] = kwargs["env"]

        def communicate(self, timeout=None):
            response = {"ok": True, "data": {"instances": [], "summary": {"count": 0}}}
            Path(captured["env"]["KDEBUG_TCL_RESPONSE_JSON"]).write_text(
                json.dumps(response), encoding="utf-8"
            )
            return "", ""

        def kill(self):
            return None

    monkeypatch.setattr(engine, "find_verdi", lambda: "/fake/verdi")
    monkeypatch.setattr(engine.subprocess, "Popen", FakePopen)
    request = {
        "action": "module.find_instances",
        "target": {"daidir": str(elab), "fsdb": str(fsdb)},
        "args": {"definition": "Target"},
    }
    ok, _ = engine.run_tcl_npi(request, {"target": {}})

    assert ok is True
    assert "-dbdir" not in captured["command"]
    assert captured["command"][-2:] == ["-ssf", str(fsdb)]
    assert captured["env"]["KDEBUG_TCL_ELAB"] == str(elab)
    assert captured["env"]["KDEBUG_TCL_DATABASE"] == str(elab.parent)
    assert engine.design_args_for_target(
        {"daidir": str(elab.parent)}, "module.find_instances"
    ) == ["-dbdir", str(elab.parent)]


@pytest.mark.contract
def test_elab_symlink_uses_resolved_native_import_path(
    kdebug_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = _load_engine(kdebug_root)
    elab = _make_elab_dir(tmp_path / "database")
    alias = tmp_path / "native_elab_alias"
    try:
        alias.symlink_to(elab, target_is_directory=True)
    except OSError as exc:
        pytest.skip("directory symlinks are unavailable: %s" % exc)
    captured = {}

    class FakePopen:
        returncode = 0

        def __init__(self, command, **kwargs):
            captured["command"] = command
            captured["env"] = kwargs["env"]

        def communicate(self, timeout=None):
            response = {"ok": True, "data": {"instances": [], "summary": {"count": 0}}}
            Path(captured["env"]["KDEBUG_TCL_RESPONSE_JSON"]).write_text(
                json.dumps(response), encoding="utf-8"
            )
            return "", ""

        def kill(self):
            return None

    monkeypatch.setattr(engine, "find_verdi", lambda: "/fake/verdi")
    monkeypatch.setattr(engine.subprocess, "Popen", FakePopen)
    ok, _ = engine.run_tcl_npi(
        {
            "action": "module.find_instances",
            "target": {"daidir": str(alias)},
            "args": {"definition": "Target"},
        },
        {"target": {}},
    )

    resolved = str(elab.resolve())
    assert ok is True
    assert "-dbdir" not in captured["command"]
    assert captured["env"]["KDEBUG_TCL_ELAB"] == resolved
    assert captured["env"]["KDEBUG_TCL_DATABASE"] == str(elab.parent.resolve())
    assert engine.resolve_design_database({"daidir": str(alias)}) == {
        "kind": "elab",
        "path": resolved,
    }


@pytest.mark.contract
def test_daidir_target_clears_inherited_elab_selector(
    kdebug_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = _load_engine(kdebug_root)
    elab = _make_elab_dir(tmp_path)
    captured = {}

    class FakePopen:
        returncode = 0

        def __init__(self, command, **kwargs):
            captured["command"] = command
            captured["env"] = kwargs["env"]

        def communicate(self, timeout=None):
            response = {"ok": True, "data": {"instances": [], "summary": {"count": 0}}}
            Path(captured["env"]["KDEBUG_TCL_RESPONSE_JSON"]).write_text(
                json.dumps(response), encoding="utf-8"
            )
            return "", ""

        def kill(self):
            return None

    monkeypatch.setenv("KDEBUG_TCL_ELAB", str(elab))
    monkeypatch.setattr(engine, "find_verdi", lambda: "/fake/verdi")
    monkeypatch.setattr(engine.subprocess, "Popen", FakePopen)
    ok, _ = engine.run_tcl_npi(
        {
            "action": "module.find_instances",
            "target": {"daidir": str(elab.parent)},
            "args": {"definition": "Target"},
        },
        {"target": {}},
    )

    assert ok is True
    assert captured["command"][-2:] == ["-dbdir", str(elab.parent)]
    assert "KDEBUG_TCL_ELAB" not in captured["env"]


@pytest.mark.contract
@pytest.mark.parametrize(
    ("fixture_kind", "error_code", "message"),
    [
        ("missing", "KDB_NOT_FOUND", "does not exist"),
        ("file", "INVALID_KDB_PATH", "must be a directory"),
        ("empty", "INVALID_KDB_PATH", "directory is empty"),
    ],
)
def test_invalid_elab_target_fails_before_verdi_spawn(
    fixture_kind: str,
    error_code: str,
    message: str,
    kdebug_root: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = _load_engine(kdebug_root)
    elab = tmp_path / "kdb.elab++"
    if fixture_kind == "file":
        elab.write_text("not a directory", encoding="utf-8")
    elif fixture_kind == "empty":
        elab.mkdir()

    def unexpected_verdi_lookup():
        pytest.fail("Verdi lookup must not run for an invalid elab target")

    monkeypatch.setattr(engine, "find_verdi", unexpected_verdi_lookup)
    ok, error = engine.run_tcl_npi(
        {
            "action": "module.find_instances",
            "target": {"daidir": str(elab)},
            "args": {"definition": "Target"},
        },
        {"target": {}},
    )
    assert ok is False
    assert error["code"] == error_code
    assert message in error["message"]


@pytest.mark.contract
def test_inaccessible_elab_target_has_access_error(
    kdebug_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = _load_engine(kdebug_root)
    elab = _make_elab_dir(tmp_path)
    original_stat = engine.os.stat

    def deny_elab(path, *args, **kwargs):
        if os.fspath(path) == str(elab):
            raise OSError(errno.EACCES, "permission denied", str(elab))
        return original_stat(path, *args, **kwargs)

    monkeypatch.setattr(engine.os, "stat", deny_elab)
    with pytest.raises(engine.DesignDatabaseError) as caught:
        engine.resolve_design_database({"daidir": str(elab)})
    assert caught.value.code == "DESIGN_DB_ACCESS_FAILED"


@pytest.mark.contract
def test_tcl_imports_elab_after_l1_and_before_action(
    kdebug_root: Path, tmp_path: Path
) -> None:
    tclsh = shutil.which("tclsh")
    if not tclsh:
        pytest.skip("tclsh is unavailable")
    elab = _make_elab_dir(tmp_path)
    npi_dir = tmp_path / "npi"
    npi_dir.mkdir()
    (npi_dir / "npi_L1.tcl").write_text(
        "lappend ::elab_order source_l1\n"
        "namespace eval ::npi_L1 {}\n"
        "proc ::npi_L1::npi_mod_define_get_inst {definition output_name} {\n"
        "  upvar 1 $output_name handles\n"
        "  set handles {}\n"
        "  lappend ::elab_order action\n"
        "  return 0\n"
        "}\n",
        encoding="utf-8",
    )
    response_path = tmp_path / "response.json"
    order_path = tmp_path / "order.txt"
    wrapper = tmp_path / "elab_order.tcl"
    npi_script = (kdebug_root / "tcl_engine" / "kdebug_npi.tcl").as_posix()
    wrapper.write_text(
        """
set ::elab_order {}
proc debImport args {lappend ::elab_order "debImport:[join $args |]"}
proc debExit {} {return}
set env(NPIL1_PATH) {%s}
set env(KDEBUG_TCL_ACTION) module.find_instances
set env(KDEBUG_TCL_DEFINITION) Target
set env(KDEBUG_TCL_MAX_ROWS) 10
set env(KDEBUG_TCL_ELAB) {%s}
set env(KDEBUG_TCL_RESPONSE_JSON) {%s}
source {%s}
set fp [open {%s} w]
puts $fp [join $::elab_order "\n"]
close $fp
"""
        % (
            npi_dir.as_posix(),
            elab.as_posix(),
            response_path.as_posix(),
            npi_script,
            order_path.as_posix(),
        ),
        encoding="utf-8",
    )
    completed = subprocess.run(
        [tclsh, str(wrapper)], capture_output=True, text=True, timeout=20
    )
    assert completed.returncode == 0, completed.stderr
    assert order_path.read_text(encoding="utf-8").splitlines() == [
        "source_l1",
        "debImport:-elab|%s" % elab.as_posix(),
        "action",
    ]
    assert json.loads(response_path.read_text(encoding="utf-8"))["ok"] is True


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
