#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="$(cd "$script_dir/../.." && pwd)"
python_bin="${PYTHON:-}"
if [[ -z "$python_bin" ]]; then
  for candidate in /usr/local/bin/python3.11 /usr/local/bin/python3.10 \
    /usr/local/bin/python3.9 /usr/local/bin/python3.8 \
    python3.11 python3.10 python3.9 python3.8 python3 python; do
    if { [[ -x "$candidate" ]] || command -v "$candidate" >/dev/null 2>&1; } && \
       "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 8) else 1)' \
         >/dev/null 2>&1; then
      python_bin="$candidate"
      break
    fi
  done
fi
[[ -n "$python_bin" ]] || {
  echo "ERROR: Python 3.8 or newer is required for KVerif CLI tests" >&2
  exit 2
}
tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

chmod +x "$root/tools/kverif" "$script_dir/fake_kdebug.py" "$script_dir/fake_kdebug.sh"
export PYTHONPATH="$root/kverif_cli/src${PYTHONPATH:+:${PYTHONPATH}}"
export PYTHON="$python_bin"
if [[ "${OS:-}" == "Windows_NT" ]]; then
  fake_kdebug="$script_dir/fake_kdebug.cmd"
else
  fake_kdebug="$script_dir/fake_kdebug.sh"
fi

"$python_bin" -m unittest discover -s "$script_dir" -v

mkdir -p "$tmp_dir/simv.daidir"
touch "$tmp_dir/waves.fsdb"
mkdir -p "$tmp_dir/verdi/bin" "$tmp_dir/verdi/share/NPI/L1/TCL" "$tmp_dir/vcs/bin"
touch "$tmp_dir/verdi/bin/verdi" "$tmp_dir/verdi/share/NPI/L1/TCL/npi_L1.tcl" \
  "$tmp_dir/vcs/bin/vcs"

VERDI_HOME="$tmp_dir/verdi" VCS_HOME="$tmp_dir/vcs" \
  "$root/tools/kverif" doctor --require-vcs \
    --kdebug-bin "$fake_kdebug" --json > "$tmp_dir/doctor.stdout.json"

"$root/tools/kverif" inspect-module \
  --input "$tmp_dir/simv.daidir" \
  --module npi_fixture_top.u_alu \
  --kdebug-bin "$fake_kdebug" \
  --out "$tmp_dir/module" --json > "$tmp_dir/module.stdout.json"

"$root/tools/kverif" trace-signal \
  --input "$tmp_dir/waves.fsdb" \
  --signal tb.dut.count --begin 0ns --end 100ns \
  --kdebug-bin "$fake_kdebug" \
  --out "$tmp_dir/wave" --json > "$tmp_dir/wave.stdout.json"

"$root/tools/kverif" tutorial waveform \
  --kdebug-bin "$fake_kdebug" \
  --out "$tmp_dir/tutorial" --json > "$tmp_dir/tutorial.stdout.json"

"$root/tools/kverif" tutorial module-inspect \
  --daidir "$tmp_dir/simv.daidir" \
  --kdebug-bin "$fake_kdebug" \
  --out "$tmp_dir/tutorial" --json > "$tmp_dir/tutorial-module.stdout.json"

"$root/tools/kverif" tutorial all \
  --daidir "$tmp_dir/simv.daidir" \
  --kdebug-bin "$fake_kdebug" \
  --out "$tmp_dir/tutorial-all" --json > "$tmp_dir/tutorial-all.stdout.json"

for language in sh csh perl python; do
  "$root/tools/kverif" new signal-check \
    --lang "$language" --out "$tmp_dir/starter-$language" --json \
    > "$tmp_dir/starter-$language.json"
done

"$python_bin" - "$tmp_dir" <<'PY'
import json
import os
import sys

root = sys.argv[1]

def load(name):
    with open(os.path.join(root, name), encoding="utf-8") as stream:
        return json.load(stream)

module = load("module.stdout.json")
assert module["ok"] and module["summary"]["parameter_count"] == 2
assert {row["name"]: row["direction"] for row in module["ports"]} == {
    "lhs": "input", "rhs": "input", "result": "output"
}
wave = load("wave.stdout.json")
assert wave["ok"] and wave["summary"]["change_count"] == 5
tutorial = load("tutorial.stdout.json")
assert tutorial["tutorial"]["passed"] is True
doctor = load("doctor.stdout.json")
assert doctor["ok"] and doctor["summary"]["required_failures"] == 0
module_tutorial = load("tutorial-module.stdout.json")
assert module_tutorial["tutorial"]["passed"] is True
all_tutorials = load("tutorial-all.stdout.json")
assert all_tutorials["ok"] and all_tutorials["summary"]["passed"] == 2
for language in ("sh", "csh", "perl", "python"):
    assert load("starter-%s.json" % language)["ok"] is True
PY

echo "PASS: KVerif beginner CLI contracts"
