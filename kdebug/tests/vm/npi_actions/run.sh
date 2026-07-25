#!/usr/bin/env bash
set -euo pipefail

if [[ $(id -un) == root ]]; then
  echo "ERROR: run this VM test as an ordinary user (expected: host)" >&2
  exit 2
fi

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
KVERIF_HOME=${KVERIF_HOME:-$(cd -- "$SCRIPT_DIR/../../../.." && pwd)}
KDEBUG=${KDEBUG_BIN:-$KVERIF_HOME/tools/kdebug}
OUT=${1:-/home/host/kverif_npi_action_test}
RESPONSES=$OUT/responses

export VERDI_HOME=${VERDI_HOME:-/home/synopsys/verdi/Verdi_O-2018.09-SP2}
export VCS_HOME=${VCS_HOME:-/home/synopsys/vcs/O-2018.09-SP2}
export VCS_TARGET_ARCH=${VCS_TARGET_ARCH:-linux64}
export PATH="$VCS_HOME/bin:$VERDI_HOME/bin:$PATH"
export LM_LICENSE_FILE=${LM_LICENSE_FILE:-27000@IC_EDA}
export SNPSLMD_LICENSE_FILE=${SNPSLMD_LICENSE_FILE:-27000@IC_EDA}

rm -rf -- "$OUT"
mkdir -p -- "$RESPONSES" "$OUT/design" "$OUT/power" "$OUT/crdb"

require_ok() {
  local response=$1
  /usr/bin/python3 - "$response" <<'PY'
import json
import sys

path = sys.argv[1]
with open(path, encoding="utf-8") as fp:
    response = json.load(fp)
if not response.get("ok"):
    error = response.get("error", {})
    raise SystemExit("%s: %s" % (error.get("code", "UNKNOWN"), error.get("message", "")))
PY
}

run_action() {
  local name=$1
  shift
  "$KDEBUG" --json action "$name" "$@" > "$RESPONSES/$name.json"
  require_ok "$RESPONSES/$name.json"
}

run_action_allow_license_block() {
  local name=$1
  shift
  if "$KDEBUG" --json action "$name" "$@" > "$RESPONSES/$name.json"; then
    require_ok "$RESPONSES/$name.json"
    return
  fi
  /usr/bin/python3 - "$RESPONSES/$name.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as fp:
    response = json.load(fp)
code = response.get("error", {}).get("code", "")
if code != "LICENSE_UNAVAILABLE":
    raise SystemExit("unexpected action failure: %s" % code)
PY
}

echo "[1/6] build public KDebug and tiny VCS database"
make -C "$KVERIF_HOME/kdebug" all >/dev/null
(
  cd "$OUT/design"
  vcs -full64 -sverilog -kdb -lca -debug_access+all -Xdump_vcsdb \
    "$SCRIPT_DIR/design.sv" -top npi_fixture_top -o simv \
    > vcs-build.log 2>&1
)
DAIDIR=$OUT/design/simv.daidir

echo "[2/6] capability, Netlist, Text, DM, and VCS actions"
run_action npi.capabilities
run_action netlist.resolve --daidir "$DAIDIR" \
  --arg name=npi_fixture_top.result --arg object_type=npiNlNet
run_action netlist.iterate --daidir "$DAIDIR" \
  --arg name=npi_fixture_top --arg object_type=npiNlNet --limit max_rows=100
run_action text.line --daidir "$DAIDIR" \
  --arg file="$SCRIPT_DIR/design.sv" --arg line=7
run_action text.words --daidir "$DAIDIR" \
  --arg file="$SCRIPT_DIR/design.sv" --arg line=7 --limit max_rows=50
run_action text.replace_line --daidir "$DAIDIR" \
  --arg file="$SCRIPT_DIR/design.sv" --arg line=7 \
  --arg 'content=    result = lhs - rhs;' \
  --arg output="$OUT/design/design.patched.sv"
run_action dm.add_net --daidir "$DAIDIR" \
  --arg module=npi_fixture_top --arg name=debug_bus \
  --arg net_type=npiDmNetWire --arg packed_left=7 --arg packed_right=0 \
  --arg output_dir="$OUT/design/dm-add-net"
run_action dm.clone_module --daidir "$DAIDIR" \
  --arg module=npi_fixture_alu --arg new_name=npi_fixture_alu_clone \
  --arg output_dir="$OUT/design/dm-clone"
run_action vcs.summary --daidir "$DAIDIR"

echo "[3/6] transaction and signal FSDB writer actions"
run_action transaction.writer.create \
  --arg output="$OUT/transactions.fsdb" --arg unit=1ns \
  --arg begin_time=0 --arg stream=bus.requests \
  --arg 'transactions=[{"start_delta":10,"duration":20,"type":"npiFsdbwTransTransaction","label":"req0","tags":["read"]},{"start_delta":5,"duration":10,"type":"npiFsdbwTransTransaction","label":"rsp0"}]' \
  --arg 'relations=[{"relation":"npiFsdbwRelParentChild","master":0,"slave":1}]'
run_action fsdb.writer.create_scope \
  --arg output="$OUT/hierarchy.fsdb" --arg unit=1ns \
  --arg begin_time=0 --arg end_time_delta=100 \
  --arg 'operations=[{"op":"scope","type":"npiFsdbScopeSvModule","name":"top"},{"op":"scope","type":"npiFsdbScopeSvModule","name":"u_a"},{"op":"up"},{"op":"scope","type":"npiFsdbScopeSvModule","name":"u_b"}]'
run_action scope.list --fsdb "$OUT/hierarchy.fsdb" --path top --limit max_rows=100

if "$KDEBUG" --json action fsdb.writer.create_scope \
     --arg output="$OUT/hierarchy.fsdb" \
     --arg 'scopes=[{"name":"must_not_overwrite"}]' \
     > "$RESPONSES/fsdb.writer.overwrite_guard.json"; then
  echo "ERROR: writer unexpectedly overwrote an existing FSDB" >&2
  exit 1
fi

echo "[4/6] source-loaded power-aware design and Power Model actions"
POWER_DEMO=$VERDI_HOME/demo/power/upf_demo
cp -R -- "$POWER_DEMO/." "$OUT/power/"
POWER_FILELIST=$OUT/power/run.f
POWER_UPF=$OUT/power/demo.upf
run_action_allow_license_block power.resolve \
  --target filelist="$POWER_FILELIST" --target upf="$POWER_UPF" \
  --target workdir="$OUT/power" --target 'defines=["NOVAS_UPF_PKG"]' \
  --arg name=system/PD_TOP --arg object_type=npiPwPowerDomain
run_action_allow_license_block power.list \
  --target filelist="$POWER_FILELIST" --target upf="$POWER_UPF" \
  --target workdir="$OUT/power" --target 'defines=["NOVAS_UPF_PKG"]' \
  --arg name=system/PD_TOP --arg object_type=npiPwElement --limit max_rows=100

echo "[5/6] CRDB creation and CRDB actions"
crdb -crdb "$OUT/crdb/dut.crdb" \
  -RTL "-sv $SCRIPT_DIR/crdb_rtl.sv -top npi_crdb_top" \
  -GATE "$SCRIPT_DIR/crdb_gate.v -top npi_crdb_top" \
  > "$OUT/crdb/crdb-build.log" 2>&1
run_action crdb.resolve \
  --arg crdb="$OUT/crdb/dut.crdb" --arg name=npi_crdb_top.state --arg level=RTL
run_action crdb.correlates \
  --arg crdb="$OUT/crdb/dut.crdb" --arg name=npi_crdb_top.state --arg level=RTL \
  --limit max_rows=100
/usr/bin/python3 - "$RESPONSES/crdb.correlates.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as fp:
    response = json.load(fp)
if response.get("data", {}).get("count", 0) < 1:
    raise SystemExit("CRDB correlation action returned no mapped objects")
PY

echo "[6/6] verify artifacts and write summary"
test -s "$OUT/transactions.fsdb"
test -s "$OUT/hierarchy.fsdb"
test -s "$OUT/design/design.patched.sv"
find "$OUT/design/dm-add-net" -type f -size +0c -print -quit | grep -q .
find "$OUT/design/dm-clone" -type f -size +0c -print -quit | grep -q .

/usr/bin/python3 - "$RESPONSES" "$OUT/npi_action_vm_test_summary.json" <<'PY'
import json
import os
import sys

response_dir, output = sys.argv[1:]
actions = {}
for name in sorted(os.listdir(response_dir)):
    if not name.endswith(".json"):
        continue
    with open(os.path.join(response_dir, name), encoding="utf-8") as fp:
        response = json.load(fp)
    action = name[:-5] if name == "fsdb.writer.overwrite_guard.json" else (
        response.get("action") or name[:-5]
    )
    actions[action] = {
        "ok": bool(response.get("ok")),
        "summary": response.get("summary", {}),
        "error_code": (response.get("error") or {}).get("code", ""),
    }
license_blocked_actions = sorted(
    name for name, item in actions.items()
    if item["error_code"] == "LICENSE_UNAVAILABLE"
)
unexpected_failures = sorted(
    name for name, item in actions.items()
    if not item["ok"]
    and item["error_code"] not in ("LICENSE_UNAVAILABLE", "OUTPUT_EXISTS")
)
summary = {
    "schema": "kdebug.npi-actions.vm-test.v1",
    "user": os.environ.get("USER", ""),
    "verdi_home": os.environ.get("VERDI_HOME", ""),
    "actions": actions,
    "passed": not unexpected_failures,
    "license_blocked_actions": license_blocked_actions,
    "unexpected_failures": unexpected_failures,
    "overwrite_guard_code": actions.get("fsdb.writer.overwrite_guard", {}).get("error_code", ""),
}
with open(output, "w", encoding="utf-8") as fp:
    json.dump(summary, fp, ensure_ascii=False, indent=2)
    fp.write("\n")
if not summary["passed"] or summary["overwrite_guard_code"] != "OUTPUT_EXISTS":
    raise SystemExit(1)
PY

echo "PASS: $OUT/npi_action_vm_test_summary.json"
