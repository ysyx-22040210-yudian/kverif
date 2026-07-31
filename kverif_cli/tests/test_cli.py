from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from kverif_cli import cli
from kverif_cli.doctor import run_doctor
from kverif_cli.scaffold import LANGUAGE_FILES, create_signal_check
from kverif_cli.runtime import KVerifError, run_json_command
from kverif_cli.tasks import inspect_module, trace_signal


ROOT = Path(__file__).resolve().parents[2]
RESPONSES = ROOT / "kdebug" / "tests" / "vm" / "npi_actions" / "evidence" / "responses"


class TaskResultTests(unittest.TestCase):
    def test_runtime_decodes_a_real_subprocess_response(self) -> None:
        fake = Path(__file__).with_name("fake_kdebug.py")
        response, completed = run_json_command([sys.executable, str(fake), "--json", "actions"])
        self.assertEqual(completed.returncode, 0)
        self.assertTrue(response["ok"])
        self.assertIn("module.inspect", response["data"]["actions"])

    def test_inspect_module_simplifies_real_archived_npi_response(self) -> None:
        response = json.loads((RESPONSES / "module.inspect.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as tmp, mock.patch(
            "kverif_cli.tasks.find_tool", return_value="/opt/kverif/tools/kdebug"
        ), mock.patch(
            "kverif_cli.tasks.run_json_command", return_value=(response, mock.Mock())
        ):
            daidir = Path(tmp) / "simv.daidir"
            daidir.mkdir()
            result = inspect_module(
                daidir=str(daidir),
                module="npi_fixture_top.u_alu",
                sections=("parameters", "ports", "instances"),
                output_dir=Path(tmp),
            )

            parameters = {row["name"]: str(row["value"]) for row in result["parameters"]}
            ports = {row["name"]: row["direction"] for row in result["ports"]}
            self.assertEqual(parameters["WIDTH"], "12")
            self.assertEqual(parameters["BIAS"], "1")
            self.assertEqual(ports, {"lhs": "input", "rhs": "input", "result": "output"})
            self.assertTrue(Path(result["artifacts"]["result"]).is_file())
            self.assertTrue(Path(result["artifacts"]["tool_response"]).is_file())
            self.assertTrue(Path(result["artifacts"]["replay"]).is_file())

    def test_trace_signal_preserves_evidence_and_summary(self) -> None:
        response = {
            "api_version": "kdebug.v1",
            "action": "signal.scan",
            "ok": True,
            "summary": {"change_count": 5, "unknown_count": 0, "truncated": False},
            "data": {"changes": [{"time": "45ns", "value": "1"}]},
        }
        with tempfile.TemporaryDirectory() as tmp, mock.patch(
            "kverif_cli.tasks.find_tool", return_value="/opt/kverif/tools/kdebug"
        ), mock.patch(
            "kverif_cli.tasks.run_json_command", return_value=(response, mock.Mock())
        ):
            fsdb = Path(tmp) / "waves.fsdb"
            fsdb.write_bytes(b"FSDB")
            result = trace_signal(
                fsdb=str(fsdb),
                signal="top.count",
                begin="0ns",
                end="100ns",
                output_dir=Path(tmp),
            )
            self.assertEqual(result["summary"]["change_count"], 5)
            self.assertEqual(result["summary"]["unknown_count"], 0)
            self.assertEqual(result["changes"][0]["time"], "45ns")

    def test_invalid_module_section_fails_before_tool_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, mock.patch(
            "kverif_cli.tasks.run_json_command"
        ) as run_command:
            daidir = Path(tmp) / "simv.daidir"
            daidir.mkdir()
            with self.assertRaises(KVerifError) as caught:
                inspect_module(
                    daidir=str(daidir),
                    module="top.u",
                    sections=("parameters", "not_a_section"),
                    output_dir=Path(tmp) / "out",
                )
            self.assertEqual(caught.exception.code, "INVALID_MODULE_SECTION")
            run_command.assert_not_called()

    def test_tool_failure_keeps_response_and_replay_artifacts(self) -> None:
        failure = KVerifError(
            "MODULE_NOT_FOUND",
            "module was not found",
            details={
                "response": {
                    "api_version": "kdebug.v1",
                    "action": "module.inspect",
                    "ok": False,
                    "error": {"code": "MODULE_NOT_FOUND", "message": "module was not found"},
                }
            },
        )
        with tempfile.TemporaryDirectory() as tmp, mock.patch(
            "kverif_cli.tasks.find_tool", return_value="/opt/kverif/tools/kdebug"
        ), mock.patch("kverif_cli.tasks.run_json_command", side_effect=failure):
            daidir = Path(tmp) / "simv.daidir"
            daidir.mkdir()
            output = Path(tmp) / "out"
            with self.assertRaises(KVerifError) as caught:
                inspect_module(
                    daidir=str(daidir),
                    module="top.missing",
                    output_dir=output,
                )
            artifacts = caught.exception.details["artifacts"]
            self.assertTrue(Path(artifacts["error"]).is_file())
            self.assertTrue(Path(artifacts["tool_response"]).is_file())
            self.assertTrue(Path(artifacts["replay"]).is_file())

    def test_json_mode_writes_only_one_json_document(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                rc = cli.run(
                    [
                        "trace-signal",
                        "--input",
                        "fixture.fsdb",
                        "--signal",
                        "top.count",
                        "--begin",
                        "0ns",
                        "--end",
                        "100ns",
                        "--dry-run",
                        "--json",
                        "--out",
                        tmp,
                    ]
                )
            payload = json.loads(stdout.getvalue())
            self.assertEqual(rc, 0)
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["command"], "trace-signal")


class DoctorTests(unittest.TestCase):
    def test_doctor_passes_with_explicit_fake_eda_homes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            verdi = base / "verdi"
            vcs = base / "vcs"
            (verdi / "bin").mkdir(parents=True)
            (verdi / "share" / "NPI" / "L1" / "TCL").mkdir(parents=True)
            (vcs / "bin").mkdir(parents=True)
            (verdi / "bin" / "verdi").write_text("", encoding="utf-8")
            (verdi / "share" / "NPI" / "L1" / "TCL" / "npi_L1.tcl").write_text(
                "", encoding="utf-8"
            )
            (vcs / "bin" / "vcs").write_text("", encoding="utf-8")
            environment = {
                "KVERIF_HOME": str(ROOT),
                "VERDI_HOME": str(verdi),
                "VCS_HOME": str(vcs),
            }
            with mock.patch.dict(os.environ, environment, clear=False):
                report = run_doctor(
                    kdebug_bin=str(ROOT / "tools" / "kdebug"),
                    require_vcs=True,
                    skip_probe=True,
                )
            self.assertTrue(report["ok"])
            self.assertEqual(report["summary"]["required_failures"], 0)


class ScaffoldTests(unittest.TestCase):
    def test_all_language_scaffolds_only_use_public_cli_examples(self) -> None:
        for language in LANGUAGE_FILES:
            with self.subTest(language=language), tempfile.TemporaryDirectory() as tmp:
                output = Path(tmp) / "starter"
                result = create_signal_check(language=language, output_dir=output)
                self.assertTrue(result["ok"])
                self.assertTrue((output / "example.sh").is_file())
                self.assertTrue((output / "expected.json").is_file())
                copied = output / LANGUAGE_FILES[language][1]
                source = copied.read_text(encoding="utf-8")
                self.assertNotIn("source kdebug_npi.tcl", source)
                self.assertNotIn("import kdebug", source)
                self.assertIn("kdebug", source.lower())


if __name__ == "__main__":
    unittest.main()
