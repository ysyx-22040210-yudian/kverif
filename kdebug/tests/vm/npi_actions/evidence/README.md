# Verdi O-2018.09-SP2 VM evidence

This directory records the machine-readable result of running `../run.sh` as the
ordinary VM user `host` on 2026-07-24.

- `vm-summary.json` is the aggregate result.
- `responses/` contains the public KDebug JSON response for every action and the
  overwrite guard.
- Generated FSDB, CRDB, VCS database, and DM output directories are checked by
  the harness but are not committed because they are large and installation-specific.

The VM did not provide the Synopsys `PowerAwareAnalysis` license feature. The
Power actions were launched against the installed Verdi UPF demo and returned
`LICENSE_UNAVAILABLE`; this is recorded as an infrastructure block rather than an
implementation pass. All other actions completed successfully.
