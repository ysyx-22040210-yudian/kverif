#!/usr/bin/env bash
set -euo pipefail

if [[ $(id -un) == root ]]; then
  echo "ERROR: run this VM stress test as an ordinary user (expected: host)" >&2
  exit 2
fi

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
KVERIF_HOME=${KVERIF_HOME:-$(cd -- "$SCRIPT_DIR/../../../.." && pwd)}
KDEBUG=${KDEBUG_BIN:-$KVERIF_HOME/tools/kdebug}
OUT=${1:-/home/host/kverif_npi_action_stress}
ITERATIONS=${KDEBUG_STRESS_ITERATIONS:-10}
PARALLEL=${KDEBUG_STRESS_PARALLEL:-2}

export VERDI_HOME=${VERDI_HOME:-/home/synopsys/verdi/Verdi_O-2018.09-SP2}
export VCS_HOME=${VCS_HOME:-/home/synopsys/vcs/O-2018.09-SP2}
export VCS_TARGET_ARCH=${VCS_TARGET_ARCH:-linux64}
export PATH="$VCS_HOME/bin:$VERDI_HOME/bin:$PATH"
export LM_LICENSE_FILE=${LM_LICENSE_FILE:-27000@IC_EDA}
export SNPSLMD_LICENSE_FILE=${SNPSLMD_LICENSE_FILE:-27000@IC_EDA}

case "$ITERATIONS" in
  ''|*[!0-9]*) echo "ERROR: KDEBUG_STRESS_ITERATIONS must be a positive integer" >&2; exit 2 ;;
esac
case "$PARALLEL" in
  ''|*[!0-9]*) echo "ERROR: KDEBUG_STRESS_PARALLEL must be a positive integer" >&2; exit 2 ;;
esac
if (( ITERATIONS < 1 || PARALLEL < 1 )); then
  echo "ERROR: stress iterations and parallelism must be greater than zero" >&2
  exit 2
fi
if [[ ! -x "$KDEBUG" ]]; then
  echo "ERROR: public KDebug executable is missing: $KDEBUG" >&2
  exit 2
fi
if [[ -e "$OUT" ]]; then
  echo "ERROR: output path already exists; choose a fresh path: $OUT" >&2
  exit 2
fi

mkdir -p -- "$OUT"

if [[ -n "${KDEBUG_STRESS_FIXTURE_ROOT:-}" ]]; then
  FIXTURE_ROOT=$KDEBUG_STRESS_FIXTURE_ROOT
  SOURCE_FILE=${KDEBUG_STRESS_SOURCE_FILE:-$SCRIPT_DIR/design.sv}
  SETUP_MODE=reused
else
  FIXTURE_ROOT=$OUT/fixture
  SOURCE_FILE=$SCRIPT_DIR/design.sv
  SETUP_MODE=fresh
  mkdir -p -- "$FIXTURE_ROOT/design" "$FIXTURE_ROOT/power" "$FIXTURE_ROOT/crdb"

  echo "[setup 1/3] build public KDebug and VCS database"
  make -C "$KVERIF_HOME/kdebug" all > "$OUT/kdebug-build.log" 2>&1
  (
    cd "$FIXTURE_ROOT/design"
    vcs -full64 -sverilog -kdb -lca -debug_access+all -Xdump_vcsdb \
      "$SOURCE_FILE" -top npi_fixture_top -o simv \
      > vcs-build.log 2>&1
  )

  echo "[setup 2/3] copy installed Power demo"
  POWER_DEMO=$VERDI_HOME/demo/power/upf_demo
  if [[ ! -d "$POWER_DEMO" ]]; then
    echo "ERROR: installed Verdi Power demo is missing: $POWER_DEMO" >&2
    exit 2
  fi
  cp -R -- "$POWER_DEMO/." "$FIXTURE_ROOT/power/"

  echo "[setup 3/3] build CRDB fixture"
  crdb -crdb "$FIXTURE_ROOT/crdb/dut.crdb" \
    -RTL "-sv $SCRIPT_DIR/crdb_rtl.sv -top npi_crdb_top" \
    -GATE "$SCRIPT_DIR/crdb_gate.v -top npi_crdb_top" \
    > "$FIXTURE_ROOT/crdb/crdb-build.log" 2>&1
fi

for required in \
  "$FIXTURE_ROOT/design/simv.daidir" \
  "$FIXTURE_ROOT/power/run.f" \
  "$FIXTURE_ROOT/power/demo.upf" \
  "$FIXTURE_ROOT/crdb/dut.crdb" \
  "$SOURCE_FILE"; do
  if [[ ! -e "$required" ]]; then
    echo "ERROR: stress fixture input is missing: $required" >&2
    exit 2
  fi
done

printf -v REPRO_COMMAND \
  'KDEBUG_STRESS_ITERATIONS=%q KDEBUG_STRESS_PARALLEL=%q KVERIF_HOME=%q KDEBUG_BIN=%q bash %q %q' \
  "$ITERATIONS" "$PARALLEL" "$KVERIF_HOME" "$KDEBUG" "$SCRIPT_DIR/stress.sh" "$OUT"
if [[ "$SETUP_MODE" == reused ]]; then
  printf -v REPRO_COMMAND \
    'KDEBUG_STRESS_FIXTURE_ROOT=%q KDEBUG_STRESS_SOURCE_FILE=%q %s' \
    "$FIXTURE_ROOT" "$SOURCE_FILE" "$REPRO_COMMAND"
fi
export KDEBUG_STRESS_COMMAND=$REPRO_COMMAND

echo "[stress] 22 actions, 15 module.objects kinds, $ITERATIONS iterations, parallel=$PARALLEL"
exec /usr/bin/python3 "$SCRIPT_DIR/stress_runner.py" \
  --kdebug "$KDEBUG" \
  --fixture-root "$FIXTURE_ROOT" \
  --source-file "$SOURCE_FILE" \
  --output "$OUT" \
  --iterations "$ITERATIONS" \
  --parallel "$PARALLEL" \
  --setup-mode "$SETUP_MODE"
