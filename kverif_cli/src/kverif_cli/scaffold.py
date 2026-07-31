from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict

from .runtime import KVerifError, repository_root


LANGUAGE_FILES = {
    "sh": ("sh/signal_health.sh", "sh/signal_health.sh", "bash"),
    "csh": ("csh/signal_health.csh", "csh/signal_health.csh", "csh"),
    "perl": ("perl/signal_health.pl", "perl/signal_health.pl", "perl"),
    "python": ("py/signal_health.py", "py/signal_health.py", "python3"),
}


def _make_executable(path: Path) -> None:
    try:
        path.chmod(path.stat().st_mode | 0o111)
    except OSError:
        pass


def create_signal_check(*, language: str, output_dir: Path, force: bool = False) -> Dict[str, Any]:
    if language not in LANGUAGE_FILES:
        raise KVerifError("INVALID_LANGUAGE", "unsupported scaffold language: %s" % language)
    root = repository_root()
    source_root = root / "examples" / "secondary_development"
    output_dir = output_dir.expanduser().resolve()
    if output_dir.exists() and any(output_dir.iterdir()) and not force:
        raise KVerifError(
            "OUTPUT_NOT_EMPTY",
            "the scaffold output directory is not empty: %s" % output_dir,
            hint="Choose an empty directory or pass --force to overwrite known scaffold files.",
        )
    output_dir.mkdir(parents=True, exist_ok=True)

    source_rel, destination_rel, interpreter = LANGUAGE_FILES[language]
    source = source_root / source_rel
    destination = output_dir / destination_rel
    if not source.is_file():
        raise KVerifError("SCAFFOLD_SOURCE_MISSING", "missing bundled example: %s" % source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    shutil.copy2(source_root / "json_response.py", output_dir / "json_response.py")
    _make_executable(destination)

    example = output_dir / "example.sh"
    example.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
: "${KVERIF_HOME:=/opt/kverif}"
fixture="$KVERIF_HOME/examples/secondary_development/fixtures/fsdb_handshake"
exec %s "$script_dir/%s" \\
  --fsdb "$fixture/waves.fsdb" \\
  --signal tb_kverif_handshake.dut.accepted_count \\
  --begin 0ns --end 125ns --min-changes 5 --max-unknown 0 --require-complete \\
  --out "$script_dir/output"
""" % (interpreter, destination_rel.replace("\\", "/")),
        encoding="utf-8",
    )
    _make_executable(example)

    expected = {
        "schema": "kverif.example.signal-health.v1",
        "gate_pass": True,
        "conclusion": {"status": "HEALTHY"},
        "evidence": {
            "signal": "tb_kverif_handshake.dut.accepted_count",
            "change_count": 5,
            "unknown_count": 0,
            "truncated": False,
        },
    }
    (output_dir / "expected.json").write_text(
        json.dumps(expected, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "README.md").write_text(
        """# Signal-check starter

This project calls the installed KVerif executable and derives a signal-health conclusion.
It does not import KVerif modules, source Tcl, or contain NPI code.

## Run the bundled real-FSDB example

```bash
export KVERIF_HOME=/opt/kverif
bash ./example.sh
```

Read `output/conclusion.json` for the derived conclusion and
`output/tool-response.json` for the original KDebug evidence. Replace the FSDB,
signal, time window, and thresholds in `example.sh` when moving to a project.
""",
        encoding="utf-8",
    )
    return {
        "schema": "kverif.scaffold.v1",
        "ok": True,
        "summary": {
            "kind": "signal-check",
            "language": language,
            "output_dir": str(output_dir),
        },
        "files": [
            str(destination),
            str(output_dir / "json_response.py"),
            str(example),
            str(output_dir / "expected.json"),
            str(output_dir / "README.md"),
        ],
    }
