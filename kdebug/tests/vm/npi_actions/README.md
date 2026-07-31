# Verdi 2018 NPI action VM test

本目录用于在 Verdi/VCS O-2018.09-SP2 上验证 KDebug 的独立 Tcl NPI action。测试必须由
普通用户运行；脚本会拒绝 `root`。它直接调用 public `tools/kdebug action ...`，不会导入
KDebug Python/C++ 内部模块，也不会用 mock 结果代替 NPI。

```bash
su - host
export KVERIF_HOME=/home/host/kverif
bash /home/host/kverif/kdebug/tests/vm/npi_actions/run.sh \
  /home/host/kverif_npi_action_test
```

覆盖范围：

- tiny VCS `-kdb -Xdump_vcsdb` 设计：capability、Netlist、Text、DM、VCS；
- Verdi 自带 UPF demo 通过 `filelist+upf` source target 直接加载：Power Model；
- Verdi `crdb` 创建的 RTL/GATE correlation database：CRDB；
- transaction writer 和 signal FSDB scope writer；
- writer 默认拒绝覆盖，以及 signal FSDB 可以被 KDebug 再次打开。

每个 public response 写入输出目录的 `responses/`，最终汇总写入
`npi_action_vm_test_summary.json`。如果环境缺少某个明确命名的 Synopsys feature，action 会
记录 `LICENSE_UNAVAILABLE` 并继续执行其他域；这类结果列入 `license_blocked_actions`，不伪装
成 PASS。2026-07-24 的归档结果位于 `evidence/`。脚本不会读取或记录 API key。

## 重复压测

`run.sh` 是逐项单次功能验证；`stress.sh` 才是重复压测。它将 `module.objects` 的 15 个
`kind` 分开统计，并为 writer、Text 修改和 DM action 分配唯一输出路径。测试全程只调用
public `tools/kdebug`，不直接执行 Tcl/NPI。输出目录必须事先不存在。

```bash
ssh host@192.168.31.116

KDEBUG_STRESS_ITERATIONS=10 KDEBUG_STRESS_PARALLEL=2 \
KVERIF_HOME=/home/host/kverif \
KDEBUG_BIN=/home/host/kverif/tools/kdebug \
bash /home/host/kverif/kdebug/tests/vm/npi_actions/stress.sh \
  "/home/host/kverif_npi_action_stress_$(date +%Y%m%d_%H%M%S)"
```

结果包括 `stress-summary.json`、两个 CSV、逐次 `stress-attempts.jsonl`、完整命令以及每次
stdout/stderr。2026-07-29 的 10 次、2 路并发结果为 360 次受测调用中 340 PASS、20 次
Power license 阻塞、0 次非预期失败；另有 10 次公开 `scope.list` 重开生成的 FSDB。详细
逐 action/kind 数据见 [`evidence/stress-report.md`](evidence/stress-report.md)，中文 Word
报告见 `evidence/KDebug_NPI_VM_Stress_Test_Report_20260729.docx`。Word 报告可由
`build_stress_report_docx.py` 直接从归档 JSON/CSV 重建。
