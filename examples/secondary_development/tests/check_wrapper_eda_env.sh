#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/../../.." && pwd)"
tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

install_root="$tmp_dir/kverif install"
verdi_root="$tmp_dir/verdi install"
mkdir -p "$install_root/tools" "$install_root/kdebug" "$install_root/kcov" \
  "$verdi_root/bin" "$verdi_root/share/NPI/L1/TCL" \
  "$verdi_root/share/NPI/lib/LINUX64"

cp "$repo_root/tools/kdebug" "$install_root/tools/kdebug"
cp "$repo_root/tools/kcov" "$install_root/tools/kcov"
chmod +x "$install_root/tools/kdebug" "$install_root/tools/kcov"

cat > "$verdi_root/bin/verdi" <<'SH'
#!/usr/bin/env bash
exit 0
SH
touch "$verdi_root/share/NPI/L1/TCL/npi_L1.tcl"
chmod +x "$verdi_root/bin/verdi"

cat > "$install_root/kdebug/kdebug" <<'SH'
#!/usr/bin/env bash
printf 'VERDI_HOME=%s\n' "${VERDI_HOME:-}"
printf 'NPIL1_PATH=%s\n' "${NPIL1_PATH:-}"
printf 'LD_LIBRARY_PATH=%s\n' "${LD_LIBRARY_PATH:-}"
SH
chmod +x "$install_root/kdebug/kdebug"

cat > "$tmp_dir/env-python" <<'SH'
#!/usr/bin/env bash
printf 'VERDI_HOME=%s\n' "${VERDI_HOME:-}"
printf 'NPIL1_PATH=%s\n' "${NPIL1_PATH:-}"
printf 'LD_LIBRARY_PATH=%s\n' "${LD_LIBRARY_PATH:-}"
SH
chmod +x "$tmp_dir/env-python"

run_and_check() {
  local output_file="$1"
  shift
  env -u VERDI_HOME -u NPIL1_PATH -u LD_LIBRARY_PATH \
    PATH="$verdi_root/bin:$PATH" "$@" > "$output_file"
  grep -Fqx "VERDI_HOME=$verdi_root" "$output_file"
  grep -Fqx "NPIL1_PATH=$verdi_root/share/NPI/L1/TCL" "$output_file"
  grep -Fq "LD_LIBRARY_PATH=$verdi_root/share/NPI/lib/LINUX64" "$output_file"
}

run_and_check "$tmp_dir/kdebug.env" "$install_root/tools/kdebug" probe
run_and_check "$tmp_dir/kcov.env" env PYTHON="$tmp_dir/env-python" "$install_root/tools/kcov" actions

echo "PASS: executable wrappers configure private NPI runtime paths"
