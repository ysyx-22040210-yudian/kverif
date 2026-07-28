# Verdi O-2018.09-SP2 VM evidence

This directory records the machine-readable result of running `../run.sh` as the
ordinary VM user `host` on 2026-07-28 (VM local time completed on 2026-07-29).

- `vm-summary.json` is the aggregate result.
- `responses/` contains the public KDebug JSON response for every action and the
  overwrite guard.
- The fixture verifies all 15 Module Library getter categories. Positive fixture
  objects cover direct and generated instances, parameters/localparams, ports,
  IO declarations, nets, variables, continuous assignments, functions, tasks,
  primitives, generate scopes, and always/initial processes. A pure SV design has
  no mixed-language boundary, so `language_interfaces` correctly returns zero.
- Assertions verify the elaborated override `WIDTH=12`, `BIAS=1`, the derived
  localparam `RESULT_WIDTH=12`, three port directions, and non-empty high/low
  connection objects for every port.
- Generated FSDB, CRDB, VCS database, and DM output directories are checked by
  the harness but are not committed because they are large and installation-specific.

The VM did not provide the Synopsys `PowerAwareAnalysis` license feature. The
Power actions were launched against the installed Verdi UPF demo and returned
`LICENSE_UNAVAILABLE`; this is recorded as an infrastructure block rather than an
implementation pass. All other actions completed successfully.
