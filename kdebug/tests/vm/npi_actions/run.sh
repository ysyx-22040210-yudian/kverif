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

run_action_as() {
  local output_name=$1
  local action_name=$2
  shift 2
  "$KDEBUG" --json action "$action_name" "$@" > "$RESPONSES/$output_name.json"
  require_ok "$RESPONSES/$output_name.json"
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

echo "[1/7] build public KDebug and tiny VCS database"
make -C "$KVERIF_HOME/kdebug" all >/dev/null
(
  cd "$OUT/design"
  vcs -full64 -sverilog -kdb -lca -debug_access+all -Xdump_vcsdb \
    "$SCRIPT_DIR/design.sv" -top npi_fixture_top -o simv \
    > vcs-build.log 2>&1
)
DAIDIR=$OUT/design/simv.daidir

echo "[2/7] Language Model and complete Module Library actions"
run_action npi.capabilities
run_action language.resolve --daidir "$DAIDIR" \
  --arg name=npi_fixture_top.u_alu
run_action language.iterate --daidir "$DAIDIR" \
  --arg name=npi_fixture_top.u_alu --arg object_type=npiParameter \
  --limit max_rows=100
run_action language.relate --daidir "$DAIDIR" \
  --arg name=npi_fixture_top.u_alu.result --arg relation_type=npiHighConn
run_action language.value --daidir "$DAIDIR" \
  --arg name=npi_fixture_top.u_alu.WIDTH --arg format=npiDecStrVal
run_action module.find_instances --daidir "$DAIDIR" \
  --arg definition=npi_fixture_alu --limit max_rows=100
run_action module.inspect --daidir "$DAIDIR" \
  --arg module=npi_fixture_top.u_alu \
  --arg 'sections=["parameters","ports","io","nets","variables","functions","continuous_assignments","always_processes"]' \
  --limit max_rows=100

while IFS='|' read -r kind module; do
  run_action_as "module.objects.$kind" module.objects --daidir "$DAIDIR" \
    --arg module="$module" --arg kind="$kind" --limit max_rows=100
done <<'MODULE_KINDS'
continuous_assignments|npi_fixture_top.u_alu
functions|npi_fixture_top.u_alu
generate_scopes|npi_fixture_top
instances|npi_fixture_top
instances_in_generate|npi_fixture_top
io|npi_fixture_top.u_alu
language_interfaces|npi_fixture_top
nets|npi_fixture_top
parameters|npi_fixture_top.u_alu
ports|npi_fixture_top.u_alu
primitives|npi_fixture_top
always_processes|npi_fixture_top.u_alu
initial_processes|npi_fixture_top
tasks|npi_fixture_top
variables|npi_fixture_top.u_alu
MODULE_KINDS

/usr/bin/python3 - "$RESPONSES" <<'PY'
import json
import os
import sys

root = sys.argv[1]

def load(name):
    with open(os.path.join(root, name + ".json"), encoding="utf-8") as fp:
        return json.load(fp)["data"]

def object_rows(data, key="items"):
    return [row.get("object", {}) for row in data.get(key, [])]

instances = object_rows(load("module.find_instances"), "instances")
if not any(row.get("full_name") == "npi_fixture_top.u_alu" for row in instances):
    raise SystemExit("module.find_instances did not return npi_fixture_top.u_alu")

value = load("language.value")
if str(value.get("value")) != "12":
    raise SystemExit("effective WIDTH parameter is not 12: %r" % value.get("value"))

parameters = load("module.objects.parameters").get("items", [])
width = next((row for row in parameters if row.get("object", {}).get("name") == "WIDTH"), None)
if width is None or str(width.get("values", {}).get("dec")) != "12":
    raise SystemExit("module parameter inventory did not expose effective WIDTH=12")

ports = object_rows(load("module.objects.ports"))
directions = {row.get("name"): row.get("direction") for row in ports}
expected_directions = {"lhs": "npiInput", "rhs": "npiInput", "result": "npiOutput"}
if directions != expected_directions:
    raise SystemExit("unexpected module port directions: %r" % directions)

port_rows = load("module.objects.ports").get("items", [])
for row in port_rows:
    name = row.get("object", {}).get("name")
    expected_full_name = "npi_fixture_top.u_alu." + name
    if row.get("object", {}).get("full_name") != expected_full_name:
        raise SystemExit("port full_name was not normalized: %r" % row)
    if row.get("object", {}).get("parent_module") != "npi_fixture_top.u_alu":
        raise SystemExit("port parent_module is missing: %r" % row)
    connections = row.get("connections", {})
    if connections.get("high") is None or connections.get("low") is None:
        raise SystemExit("port is missing high/low connection evidence: %r" % row)

io_rows = object_rows(load("module.objects.io"))
if {row.get("name") for row in io_rows} != {"lhs", "rhs", "result"}:
    raise SystemExit("module IO declarations are incomplete: %r" % io_rows)

inspect = load("module.inspect")
required_sections = {"parameters", "ports", "io", "nets", "variables", "functions", "continuous_assignments", "always_processes"}
if not required_sections.issubset(inspect.get("sections", {})):
    raise SystemExit("module.inspect is missing requested sections")

positive_kinds = {
    "continuous_assignments", "functions", "generate_scopes", "instances",
    "instances_in_generate", "io", "nets", "parameters", "ports", "primitives",
    "always_processes", "initial_processes", "tasks", "variables",
}
for kind in positive_kinds:
    data = load("module.objects." + kind)
    if data.get("count", 0) < 1:
        raise SystemExit("module.objects kind %s returned no fixture object" % kind)
PY

echo "[3/7] Netlist, Text, DM, and VCS actions"
run_action netlist.resolve --daidir "$DAIDIR" \
  --arg name=npi_fixture_top.result --arg object_type=npiNlNet
run_action netlist.iterate --daidir "$DAIDIR" \
  --arg name=npi_fixture_top --arg object_type=npiNlNet --limit max_rows=100
run_action text.line --daidir "$DAIDIR" \
  --arg file="$SCRIPT_DIR/design.sv" --arg line=27
run_action text.words --daidir "$DAIDIR" \
  --arg file="$SCRIPT_DIR/design.sv" --arg line=27 --limit max_rows=50
run_action text.replace_line --daidir "$DAIDIR" \
  --arg file="$SCRIPT_DIR/design.sv" --arg line=27 \
  --arg 'content=    sum = lhs - rhs;' \
  --arg output="$OUT/design/design.patched.sv"
run_action dm.add_net --daidir "$DAIDIR" \
  --arg module=npi_fixture_top --arg name=debug_bus \
  --arg net_type=npiDmNetWire --arg packed_left=7 --arg packed_right=0 \
  --arg output_dir="$OUT/design/dm-add-net"
run_action dm.clone_module --daidir "$DAIDIR" \
  --arg module=npi_fixture_alu --arg new_name=npi_fixture_alu_clone \
  --arg output_dir="$OUT/design/dm-clone"
run_action vcs.summary --daidir "$DAIDIR"

echo "[4/7] transaction and signal FSDB writer actions"
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

echo "[5/7] source-loaded power-aware design and Power Model actions"
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

echo "[6/7] CRDB creation and CRDB actions"
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

echo "[7/7] verify artifacts and write summary"
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
    result_name = name[:-5]
    actions[result_name] = {
        "action": response.get("action") or result_name,
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
