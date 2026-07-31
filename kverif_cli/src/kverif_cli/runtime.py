from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


Json = Dict[str, Any]


class KVerifError(RuntimeError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        hint: str = "",
        details: Optional[Json] = None,
        exit_code: int = 1,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.hint = hint
        self.details = details or {}
        self.exit_code = exit_code

    def payload(self) -> Json:
        return {
            "ok": False,
            "error": {
                "code": self.code,
                "message": self.message,
                "hint": self.hint,
                "details": self.details,
            },
        }


def repository_root() -> Path:
    configured = os.environ.get("KVERIF_HOME")
    if configured:
        return Path(configured).expanduser().resolve()
    return Path(__file__).resolve().parents[3]


def find_tool(name: str, override: Optional[str] = None) -> str:
    env_name = "%s_BIN" % name.upper().replace("-", "_")
    candidates = [override, os.environ.get(env_name)]
    root_candidate = repository_root() / "tools" / name
    candidates.append(str(root_candidate))
    candidates.append(shutil.which(name))
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate).expanduser()
        if path.exists():
            return str(path.resolve())
        located = shutil.which(str(candidate))
        if located:
            return str(Path(located).resolve())
    raise KVerifError(
        "TOOL_NOT_FOUND",
        "%s executable was not found" % name,
        hint="Set %s or KVERIF_HOME, or add %s to PATH." % (env_name, name),
    )


def command_text(argv: Iterable[str]) -> str:
    return " ".join(shlex.quote(str(item)) for item in argv)


def _decode_json(stdout: str) -> Json:
    text = stdout.strip()
    if not text:
        raise ValueError("stdout was empty")
    try:
        value = json.loads(text)
        if isinstance(value, dict):
            return value
    except json.JSONDecodeError:
        pass
    for line in reversed(text.splitlines()):
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise ValueError("stdout did not contain a JSON object")


def run_json_command(argv: List[str]) -> Tuple[Json, subprocess.CompletedProcess[str]]:
    try:
        completed = subprocess.run(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError as exc:
        raise KVerifError(
            "COMMAND_START_FAILED",
            "could not start the underlying KVerif command: %s" % exc,
            hint="Run 'kverif doctor' and verify the executable path.",
            details={"command": command_text(argv)},
        ) from exc

    try:
        response = _decode_json(completed.stdout)
    except ValueError as exc:
        raise KVerifError(
            "INVALID_TOOL_OUTPUT",
            "the underlying command did not return valid JSON",
            hint="Run the replay command directly and inspect stderr.",
            details={
                "command": command_text(argv),
                "exit_code": completed.returncode,
                "stderr": completed.stderr[-4000:],
                "stdout": completed.stdout[-4000:],
            },
        ) from exc

    if completed.returncode != 0 or not response.get("ok", False):
        error = response.get("error") or {}
        code = str(error.get("code") or "UNDERLYING_COMMAND_FAILED")
        message = str(error.get("message") or "the underlying KVerif command failed")
        raise KVerifError(
            code,
            message,
            hint="Inspect tool-response.json or run replay.sh for the original diagnostic.",
            details={
                "command": command_text(argv),
                "exit_code": completed.returncode,
                "stderr": completed.stderr[-4000:],
                "response": response,
            },
            exit_code=completed.returncode or 1,
        )
    return response, completed


def write_json(path: Path, payload: Json) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def write_replay(path: Path, argv: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "#!/usr/bin/env bash\nset -euo pipefail\nexec %s\n" % command_text(argv),
        encoding="utf-8",
    )
    try:
        path.chmod(path.stat().st_mode | 0o111)
    except OSError:
        pass


def persist_task_result(
    result: Json,
    *,
    output_dir: Path,
    argv: List[str],
    tool_response: Optional[Json],
) -> Json:
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    result_path = output_dir / "result.json"
    response_path = output_dir / "tool-response.json"
    replay_path = output_dir / "replay.sh"

    write_replay(replay_path, argv)
    if tool_response is not None:
        write_json(response_path, tool_response)
    result["artifacts"] = {
        "result": str(result_path),
        "tool_response": str(response_path) if tool_response is not None else None,
        "replay": str(replay_path),
    }
    result["underlying_command"] = command_text(argv)
    write_json(result_path, result)
    return result


def persist_task_failure(
    error: KVerifError,
    *,
    output_dir: Path,
    argv: List[str],
) -> None:
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    error_path = output_dir / "error.json"
    response_path = output_dir / "tool-response.json"
    replay_path = output_dir / "replay.sh"
    write_replay(replay_path, argv)

    response = error.details.get("response")
    if isinstance(response, dict):
        write_json(response_path, response)
    artifacts = {
        "error": str(error_path),
        "tool_response": str(response_path) if isinstance(response, dict) else None,
        "replay": str(replay_path),
    }
    error.details["artifacts"] = artifacts
    payload = {
        "schema": "kverif.task-error.v1",
        "ok": False,
        "error": error.payload()["error"],
        "underlying_command": command_text(argv),
        "artifacts": artifacts,
    }
    write_json(error_path, payload)


def direction_label(value: Any) -> str:
    labels = {
        "npiInput": "input",
        "npiOutput": "output",
        "npiInout": "inout",
        "npiMixedIO": "mixed",
    }
    text = str(value or "unknown")
    return labels.get(text, text)
