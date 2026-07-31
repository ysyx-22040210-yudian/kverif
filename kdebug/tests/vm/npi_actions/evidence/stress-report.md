# KDebug Tcl NPI action VM 压测报告

## 1. 结论

2026-07-29 在 VM `192.168.31.116` 上，由普通用户 `host` 使用 Verdi/VCS
O-2018.09 系列环境完成 KDebug 新增 Tcl NPI action 压测。测试只调用 public
`tools/kdebug` 可执行文件，没有直接执行 Tcl、NPI procedure 或导入 KDebug 内部模块。

| 指标 | 结果 |
| --- | ---: |
| 新增 action | 22 |
| 独立压测项 | 36（其中 `module.objects` 拆成 15 个 kind） |
| 每项执行次数 | 10 |
| 并发度 | 2 |
| 受测 action 调用 | 360 |
| 生成 FSDB 的公开 CLI 重开校验 | 10 |
| public KDebug CLI 总调用 | 370 |
| PASS | 340 |
| `LICENSE_BLOCKED` | 20 |
| 非预期失败 | 0 |
| 完整 PASS action | 20/22 |
| 许可证阻塞 action | 2/22（`power.resolve`、`power.list`） |
| 总墙钟时间 | 589.607215 秒 |

因此，不能表述为“22 个新增功能全部完成了功能压测”。其中 20 个 action 完成 10 次
真实功能执行且全部通过；两个 Power action 均真实启动 Verdi、加载安装内置 RTL+UPF demo，
但 10/10 次都因 VM 缺少 `PowerAwareAnalysis` feature 返回 `LICENSE_UNAVAILABLE`。
这 20 次是稳定的许可证阻塞，不是功能 PASS，也不是 KDebug 崩溃或断言失败。

## 2. 实际执行命令

以下是 `stress-command.txt` 记录的原始命令。输出目录必须不存在；再次执行时应换一个新目录。

```bash
KDEBUG_STRESS_ITERATIONS=10 KDEBUG_STRESS_PARALLEL=2 \
KVERIF_HOME=/home/host/kverif_npi_candidate_20260728_full \
KDEBUG_BIN=/home/host/kverif_npi_candidate_20260728_full/tools/kdebug \
bash /home/host/kverif_npi_candidate_20260728_full/kdebug/tests/vm/npi_actions/stress.sh \
  /home/host/kverif_npi_action_stress_20260729
```

正式安装到 `/home/host/kverif` 后，可由普通用户直接执行：

```bash
ssh host@192.168.31.116

KDEBUG_STRESS_ITERATIONS=10 KDEBUG_STRESS_PARALLEL=2 \
KVERIF_HOME=/home/host/kverif \
KDEBUG_BIN=/home/host/kverif/tools/kdebug \
bash /home/host/kverif/kdebug/tests/vm/npi_actions/stress.sh \
  "/home/host/kverif_npi_action_stress_$(date +%Y%m%d_%H%M%S)"
```

`stress.sh` 会新建 tiny VCS KDB、复制 Verdi 自带 Power demo、创建 RTL/GATE CRDB，
然后调用 `stress_runner.py`。harness 没有设置 action timeout；writer、Text 修改和 DM action
每轮使用唯一输出路径，两个并发进程也使用各自工作目录。

## 3. 22 个 action 汇总

时间单位均为秒。`module.objects` 一行汇总 15 个 kind，共 150 次。

| action | case | 次数 | PASS | license | fail | avg | p95 | max | 结果 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `npi.capabilities` | 1 | 10 | 10 | 0 | 0 | 1.926 | 2.029 | 2.040 | PASS |
| `language.resolve` | 1 | 10 | 10 | 0 | 0 | 3.125 | 3.697 | 3.730 | PASS |
| `language.iterate` | 1 | 10 | 10 | 0 | 0 | 3.071 | 3.552 | 3.565 | PASS |
| `language.relate` | 1 | 10 | 10 | 0 | 0 | 2.889 | 2.944 | 2.944 | PASS |
| `language.value` | 1 | 10 | 10 | 0 | 0 | 3.095 | 3.754 | 3.762 | PASS |
| `module.find_instances` | 1 | 10 | 10 | 0 | 0 | 3.059 | 3.449 | 3.453 | PASS |
| `module.inspect` | 1 | 10 | 10 | 0 | 0 | 3.036 | 3.438 | 3.440 | PASS |
| `module.objects` | 15 | 150 | 150 | 0 | 0 | 3.474 | 5.146 | 6.259 | PASS |
| `netlist.resolve` | 1 | 10 | 10 | 0 | 0 | 5.249 | 6.488 | 6.728 | PASS |
| `netlist.iterate` | 1 | 10 | 10 | 0 | 0 | 4.475 | 5.394 | 5.604 | PASS |
| `text.line` | 1 | 10 | 10 | 0 | 0 | 4.332 | 4.767 | 4.770 | PASS |
| `text.words` | 1 | 10 | 10 | 0 | 0 | 4.118 | 4.494 | 4.533 | PASS |
| `text.replace_line` | 1 | 10 | 10 | 0 | 0 | 3.439 | 4.557 | 4.667 | PASS |
| `dm.add_net` | 1 | 10 | 10 | 0 | 0 | 3.072 | 3.200 | 3.212 | PASS |
| `dm.clone_module` | 1 | 10 | 10 | 0 | 0 | 3.050 | 3.404 | 3.418 | PASS |
| `vcs.summary` | 1 | 10 | 10 | 0 | 0 | 2.113 | 2.347 | 2.350 | PASS |
| `power.resolve` | 1 | 10 | 0 | 10 | 0 | 3.280 | 3.660 | 3.692 | LICENSE_BLOCKED |
| `power.list` | 1 | 10 | 0 | 10 | 0 | 2.947 | 3.079 | 3.082 | LICENSE_BLOCKED |
| `crdb.resolve` | 1 | 10 | 10 | 0 | 0 | 1.807 | 1.911 | 1.911 | PASS |
| `crdb.correlates` | 1 | 10 | 10 | 0 | 0 | 1.780 | 1.858 | 1.865 | PASS |
| `transaction.writer.create` | 1 | 10 | 10 | 0 | 0 | 1.878 | 2.045 | 2.072 | PASS |
| `fsdb.writer.create_scope` | 1 | 10 | 10 | 0 | 0 | 1.783 | 1.842 | 1.843 | PASS |

完整 min/avg/p50/p95/max 数据见 `stress-action-results.csv`。

## 4. `module.objects` 15 个 kind

| kind | 次数 | PASS | fail | avg | p95 | max | 结果 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `continuous_assignments` | 10 | 10 | 0 | 2.963 | 3.416 | 3.428 | PASS |
| `functions` | 10 | 10 | 0 | 2.922 | 3.078 | 3.089 | PASS |
| `generate_scopes` | 10 | 10 | 0 | 2.840 | 2.999 | 3.021 | PASS |
| `instances` | 10 | 10 | 0 | 3.087 | 3.331 | 3.335 | PASS |
| `instances_in_generate` | 10 | 10 | 0 | 2.826 | 3.019 | 3.048 | PASS |
| `io` | 10 | 10 | 0 | 2.782 | 3.018 | 3.045 | PASS |
| `language_interfaces` | 10 | 10 | 0 | 3.177 | 3.598 | 3.605 | PASS（纯 SV 预期为 0 项） |
| `nets` | 10 | 10 | 0 | 3.200 | 3.510 | 3.533 | PASS |
| `parameters` | 10 | 10 | 0 | 3.407 | 4.346 | 4.357 | PASS |
| `ports` | 10 | 10 | 0 | 4.755 | 5.823 | 6.006 | PASS |
| `primitives` | 10 | 10 | 0 | 3.512 | 4.205 | 4.239 | PASS |
| `always_processes` | 10 | 10 | 0 | 4.258 | 4.869 | 4.905 | PASS |
| `initial_processes` | 10 | 10 | 0 | 4.399 | 6.084 | 6.259 | PASS |
| `tasks` | 10 | 10 | 0 | 3.409 | 3.598 | 3.601 | PASS |
| `variables` | 10 | 10 | 0 | 4.577 | 5.698 | 5.844 | PASS |

## 5. 每轮语义断言

| 域 | 不是只看退出码的校验内容 |
| --- | --- |
| Language/Module | `WIDTH=12`、`BIAS=1`、`RESULT_WIDTH=12`、实例定义和完整层次名 |
| Port/IO | `lhs/rhs` 为 input、`result` 为 output，三个端口的 high/low connection 均非空 |
| Module getters | direct/generate 实例、net、function、task、primitive、always/initial 等 fixture 对象存在 |
| Netlist | `npi_fixture_top.result[11:0]` 宽度为 12，iterator 返回 fixture net |
| Text | 第 27 行和 token 保持正确，替换后的新文件第 27 行为 `sum = lhs - rhs;` |
| DM | 新增 `[7:0]` net 和 clone module 的导出目录包含非空 RTL 文件 |
| VCS | 编译错误数为 0、模块数为 3、版本属于 O-2018.09 |
| CRDB | RTL `state` 可解析，并至少关联到一个 GATE 对象 |
| Transaction writer | FSDB 非空、2 个 transaction、1 个 relation、结束时间 45 |
| FSDB writer | FSDB 非空、3 个 scope/1 次 up，并由 public `scope.list` 重开得到 `top.u_a/top.u_b` |

## 6. 证据文件

| 文件 | 内容 |
| --- | --- |
| `stress-summary.json` | 环境、范围、总数、22 action 和 36 case 的结构化汇总 |
| `stress-action-results.csv` | 22 个 action 的次数、状态和耗时统计 |
| `stress-results.csv` | 36 个独立 case，含 15 个 Module kind 的统计 |
| `stress-attempts.jsonl` | 360 次调用的命令、退出码、状态、耗时、响应哈希和远端日志路径 |
| `stress-command.txt` | 实际执行命令 |
| `stress-implementation-sha256.txt` | wrapper、binary、Tcl engine、harness 和 fixture 哈希 |

VM 原始目录 `/home/host/kverif_npi_action_stress_20260729` 还保留 360 份 stdout、stderr、
10 份 FSDB 重开响应、生成文件和构建 fixture。测试结束后没有残留本轮 KDebug、Verdi 或 VCS
进程。只有在 VM 获得 `PowerAwareAnalysis` license 后重跑并得到 Power 两项 10/10 PASS，
才能把结论提升为 22/22 action 完成功能压测。
