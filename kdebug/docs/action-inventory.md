# kdebug Action Inventory

本文件冻结当前 `kdebug.v1` public action 清单，供 ActionSpec、schema、
example 和 contract test 迁移使用。状态定义：

| status | 含义 |
| --- | --- |
| `stable` | 已实现，默认可给 agent 使用，contract drift 必须被测试挡住 |
| `experimental` | 已实现但字段或行为仍可能调整，agent 不应默认优先使用 |
| `deprecated` | 仍可能存在兼容路径，但不建议新流程使用 |
| `removed` | 已移除或明确不支持，仅保留迁移说明 |

资源需求定义：

| resource | 含义 |
| --- | --- |
| `none` | 不需要 `target` 资源 |
| `design` | 需要 `target.daidir`、`target.filelist` 或包含 design 的 `session_id` |
| `waveform` | 需要 `target.fsdb` 或包含 waveform 的 `session_id` |
| `combined` | 需要 `target.daidir` + `target.fsdb`，或包含两者的 session |
| `session` | 主要操作 top-level session registry |
| `any` | `target.daidir`、`target.fsdb` 或两者至少一个 |

## Builtin / Session / Combined

| action | category | status | resource | implementation | test |
| --- | --- | --- | --- | --- | --- |
| `schema` | builtin | stable | none | top-level catalog | regression |
| `actions` | builtin | stable | none | top-level catalog | regression |
| `batch` | builtin | stable | none | top-level dispatcher | partial |
| `npi.capabilities` | builtin | experimental | none | Verdi 2018 Tcl NPI capability probe | VM PASS 2026-07-24 |
| `session.open` | session | stable | any | dispatcher + backend session managers | regression |
| `session.list` | session | stable | session | unified engine session registry | partial |
| `session.doctor` | session | stable | session | dispatcher + backend health | partial |
| `session.kill` | session | stable | session | dispatcher + backend session managers | partial |
| `session.close` | session | stable | session | alias-compatible close path | partial |
| `session.gc` | session | stable | none | dispatcher + waveform gc | partial |
| `trace.active_driver` | combined | stable | any | `ActiveTraceService` | regression |
| `trace.active_driver_chain` | combined | stable | any | `ActiveTraceChainService` | partial |

## Design Actions

| action | category | status | resource | implementation | test |
| --- | --- | --- | --- | --- | --- |
| `trace.driver` | design | stable | design | design engine forward | regression |
| `trace.load` | design | stable | design | design engine forward | partial |
| `trace.query` | design | stable | design | design engine forward | partial |
| `signal.resolve` | design | stable | design | design engine forward | partial |
| `signal.canonicalize` | design | stable | design | design engine forward | partial |
| `trace.expand` | design | stable | design | design engine forward | regression |
| `trace.graph` | design | stable | design | design engine forward | regression |
| `trace.path` | design | stable | design | design engine forward | partial |
| `trace.explain` | design | stable | design | design engine forward | partial |
| `control.explain` | design | stable | design | design engine forward | partial |
| `source.context` | design | stable | none | design engine forward | regression |
| `expr.normalize` | design | stable | none | design engine forward | partial |
| `procedural.assignment` | design | stable | design | design engine forward | partial |
| `sequential.update` | design | stable | design | design engine forward | partial |
| `fsm.explain` | design | stable | design | design engine forward | partial |
| `counter.explain` | design | stable | design | design engine forward | partial |
| `port.trace` | design | stable | design | design engine forward | partial |
| `instance.map` | design | stable | design | design engine forward | partial |
| `interface.resolve` | design | stable | design | design engine forward | partial |
| `language.resolve` | design | experimental | design | Tcl NPI Language Model object lookup and fixed property snapshot | VM PASS 2026-07-28 |
| `language.iterate` | design | experimental | design | Tcl NPI Language Model typed iterator | VM PASS 2026-07-28 |
| `language.relate` | design | experimental | design | Tcl NPI Language Model one-to-one relationship lookup | VM PASS 2026-07-28 |
| `language.value` | design | experimental | design | Tcl NPI Language Model elaborated constant/parameter value | VM PASS 2026-07-28 |
| `module.objects` | design | experimental | design | Tcl NPI Module Library 15-kind object inventory | VM PASS all 15 kinds 2026-07-28 |
| `module.find_instances` | design | experimental | design | Tcl NPI module-definition to instance lookup | VM PASS 2026-07-28 |
| `module.inspect` | design | experimental | design | Tcl NPI aggregate instance/parameter/port/IO/connectivity inspection | VM PASS 2026-07-28 |
| `netlist.resolve` | design | experimental | design | Tcl NPI Netlist Model lookup | VM PASS 2026-07-24 |
| `netlist.iterate` | design | experimental | design | Tcl NPI Netlist Model iterator | VM PASS 2026-07-24 |
| `text.line` | design | experimental | design | Tcl NPI Text Model line lookup | VM PASS 2026-07-24 |
| `text.words` | design | experimental | design | Tcl NPI Text Model word iterator | VM PASS 2026-07-24 |
| `text.replace_line` | design | experimental | design | Tcl NPI Text Model copy-on-write edit | VM PASS 2026-07-24 |
| `dm.add_net` | design | experimental | design | Tcl NPI DM add/write flow | VM PASS 2026-07-24 |
| `dm.clone_module` | design | experimental | design | Tcl NPI DM clone/write flow | VM PASS 2026-07-24 |
| `vcs.summary` | design | experimental | design | Tcl NPI VCS Model summary | VM PASS 2026-07-24 |
| `power.resolve` | design | experimental | design | Tcl NPI Power Model lookup | VM license-blocked 2026-07-24 |
| `power.list` | design | experimental | design | Tcl NPI Power Model iterator | VM license-blocked 2026-07-24 |
| `crdb.resolve` | design | experimental | none | Tcl NPI CRDB lookup | VM PASS 2026-07-24 |
| `crdb.correlates` | design | experimental | none | Tcl NPI CRDB correlation iterator | VM PASS 2026-07-24 |

## Waveform Actions

| action | category | status | resource | implementation | test |
| --- | --- | --- | --- | --- | --- |
| `cursor.set` | waveform | stable | waveform | waveform engine forward | partial |
| `cursor.get` | waveform | stable | waveform | waveform engine forward | partial |
| `cursor.list` | waveform | stable | waveform | waveform engine forward | partial |
| `cursor.delete` | waveform | stable | waveform | waveform engine forward | partial |
| `cursor.use` | waveform | stable | waveform | waveform engine forward | partial |
| `scope.list` | waveform | stable | waveform | waveform engine forward | regression |
| `signal.scan` | waveform | stable | waveform | waveform engine forward | partial |
| `rc.generate` | waveform | stable | waveform | waveform engine forward | partial |
| `value.at` | waveform | stable | waveform | waveform engine forward | regression |
| `value.batch_at` | waveform | stable | waveform | waveform engine forward | regression |
| `list.create` | waveform | stable | waveform | waveform engine forward | partial |
| `list.add` | waveform | stable | waveform | waveform engine forward | partial |
| `list.delete` | waveform | stable | waveform | waveform engine forward | partial |
| `list.show` | waveform | stable | waveform | waveform engine forward | partial |
| `list.value_at` | waveform | stable | waveform | waveform engine forward | partial |
| `list.validate` | waveform | stable | waveform | waveform engine forward | partial |
| `list.diff` | waveform | stable | waveform | waveform engine forward | partial |
| `apb.config.load` | waveform | stable | waveform | waveform engine forward | partial |
| `apb.config.list` | waveform | stable | waveform | waveform engine forward | partial |
| `apb.query` | waveform | stable | waveform | waveform engine forward | regression |
| `apb.cursor` | waveform | stable | waveform | waveform engine forward | partial |
| `axi.config.load` | waveform | stable | waveform | waveform engine forward | partial |
| `axi.config.list` | waveform | stable | waveform | waveform engine forward | partial |
| `axi.query` | waveform | stable | waveform | waveform engine forward | regression |
| `axi.cursor` | waveform | stable | waveform | waveform engine forward | partial |
| `axi.analysis` | waveform | stable | waveform | waveform engine forward | regression |
| `axi.export` | waveform | stable | waveform | waveform engine forward | targeted |
| `event.config.load` | waveform | stable | waveform | waveform engine forward | partial |
| `event.config.list` | waveform | stable | waveform | waveform engine forward | partial |
| `event.find` | waveform | stable | waveform | waveform engine forward | partial |
| `event.export` | waveform | stable | waveform | waveform engine forward | regression |
| `verify.conditions` | waveform | stable | waveform | waveform engine forward | regression |
| `expr.eval_at` | waveform | stable | waveform | waveform engine forward | partial |
| `window.verify` | waveform | stable | waveform | waveform engine forward | partial |
| `signal.changes` | waveform | stable | waveform | waveform engine forward | regression |
| `signal.stability` | waveform | stable | waveform | waveform engine forward | partial |
| `signal.trend` | waveform | stable | waveform | waveform engine forward | partial |
| `signal.statistics` | waveform | stable | waveform | waveform engine forward | regression |
| `counter.statistics` | waveform | stable | waveform | waveform engine forward | targeted |
| `sampled_pulse.inspect` | waveform | experimental | waveform | waveform engine forward | partial |
| `inspect_signal` | waveform | deprecated | waveform | waveform engine forward | partial |
| `detect_anomaly` | waveform | stable | waveform | waveform engine forward | partial |
| `handshake.inspect` | waveform | stable | waveform | waveform engine forward | regression |
| `axi.channel_stall` | waveform | experimental | waveform | waveform engine forward | partial |
| `axi.outstanding_timeline` | waveform | experimental | waveform | waveform engine forward | partial |
| `axi.request_response_pair` | waveform | experimental | waveform | waveform engine forward | partial |
| `axi.latency_outlier` | waveform | experimental | waveform | waveform engine forward | partial |
| `apb.transfer_window` | waveform | experimental | waveform | waveform engine forward | partial |
| `stream.config.load` | waveform | stable | waveform | waveform engine forward | synthetic |
| `stream.config.list` | waveform | stable | waveform | waveform engine forward | synthetic |
| `stream.show` | waveform | stable | waveform | waveform engine forward | synthetic |
| `stream.validate` | waveform | stable | waveform | waveform engine forward | synthetic |
| `stream.query` | waveform | stable | waveform | waveform engine forward | synthetic |
| `stream.export` | waveform | stable | waveform | waveform engine forward | synthetic |
| `transaction.writer.create` | waveform | experimental | none | Tcl NPI transaction FSDB writer | VM PASS 2026-07-24 |
| `fsdb.writer.create_scope` | waveform | experimental | none | Tcl NPI signal FSDB hierarchy writer | VM PASS 2026-07-24 |

## Removed Actions

| action | category | status | resource | implementation | test |
| --- | --- | --- | --- | --- | --- |
| `signal.search` | design | removed | design | removed from public catalog | regression |
