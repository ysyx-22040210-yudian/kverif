# Design batch actions

`module.inspect_batch` and `port.trace_batch` amortize design database startup across
many independent queries. Each public request starts or reuses one kdebug design
target, launches one Verdi Tcl process, opens the KDB once, and executes the
batch inside that process. A direct `target.daidir` request does not create a
named session.

## `module.inspect_batch`

Required arguments:

- `modules`: non-empty array of non-empty elaborated instance paths.
- `sections`: optional `module.inspect` section array.

Each `data.inspections[]` entry has `module`, `ok`, `data`, and `error`.
Missing instances and section query failures are isolated to the corresponding
entry. `max_rows` is applied independently to every section of every module.

## `port.trace_batch`

`module` selects an elaborated module definition. `ports` is optional; omit it
or pass an empty array to trace every port on every instance of that definition.
Selected bits such as `io_id[7]` are traced independently. `stop_instances`
stops recursive load traversal at named hierarchy endpoints.
`selection_mode` distinguishes all-port and explicit requests;
`requested_port_count` reports the filter size while `traced_port_count` reports
the actual unique instance/port pairs returned.

The action returns separate `full_rows` and `boundary_rows`. Full tracing crosses
module boundaries; boundary tracing stops on module ports. Constant driver rows
are published only when an unconditional source or exact connection provenance
is available. Each constant evidence item includes `const_full_path` and a
machine-readable `provenance.path`. Unverified, mixed, or conflicting constants
are suppressed, recorded in `errors`, and replaced by a
`TRACE_LIMIT_REACHED:constant_*` marker so downstream reports remain fail-closed.

`options.source_fallback` controls source parsing; `include_full` and
`include_boundary` select result surfaces. Limits map directly to the legacy
trace budgets: parent, assignment, expression, node, edge, API-list, and output
row limits. `limits.max_rows=0` leaves output rows unlimited. A positive value
is a strict, independent array-size budget for `full_rows` and `boundary_rows`;
when more rows exist, the final budget slot is replaced by
`TRACE_LIMIT_REACHED:row_limit` on each affected surface. Constant evidence is
marked effective only while at least one returned surface still publishes its
constant row. `target.daidir` accepts either the generated `simv.daidir` directory
or its `kdb.elab++` directory. The latter is opened natively with
`debImport -elab`; it is not rewritten to the parent daidir.

The arrays are transferred to Tcl through hex-encoded UTF-8 plan files rather
than interpolated Tcl. `module.inspect_batch` preserves request order. The
legacy port tracer returns NPI traversal order and does not promise
the order of the `ports` filter. The plan files avoid command or Tcl injection
through signal and instance names.
