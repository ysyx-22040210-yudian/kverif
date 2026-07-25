from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import jsonschema
import pytest


NEW_NPI_ACTIONS = {
    "npi.capabilities",
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
    assert len(response_paths) == 17
    for response_path in response_paths:
        response = json.loads(response_path.read_text(encoding="utf-8"))
        action = response["action"]
        schema_path = (
            kdebug_root / "schemas" / "v1" / "actions" / (action + ".response.schema.json")
        )
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator(schema).validate(response)
