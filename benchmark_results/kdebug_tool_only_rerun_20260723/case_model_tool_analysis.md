# KVerif KDebug XiangShan 最新 Benchmark 逐 Case 模型与工具作用分析

> Suite：`kdebug_tool_only_rerun_20260723`
> VM：`/home/host/kverif_runs/kdebug_tool_only_rerun_20260723`
> 本地结果：`E:\xverif\benchmark_results\kdebug_tool_only_rerun_20260723`
> 最新轮分析对象：`gpt-5.5`、`qwen3.6-35b`，仅 `with_kdebug` 组
> 最新轮明确排除：`glm-4.7`、`without_kdebug`
> 历史无工具对照：`kdebug_xiangshan_v2_run_20260630_025641_20260704_qwen_final/results.csv`

## 1. 结论摘要

1. 32 个任务全部结束，终态为 20 PASS、12 TIMEOUT。GPT-5.5 为 14/16 PASS，
   Qwen3.6-35B 为 6/16 PASS。
2. 32 个任务均有真实 KDebug manifest，且 `tool_evidence_valid=true`、
   `evidence_used` 非空。这只能证明工具调用和证据门禁有效，不能自动证明工具促成修复。
3. KDebug 对 `case_006/007/008/009/015` 的 RTL 证据最强：driver trace 直接给出
   注错常量、条件信号、源码文件和行号。GPT 能把这些证据转换成可应用补丁；Qwen 仅在
   `case_008` 成功，其余多因补丁上下文错误或修改了错误文件而超时。
4. KDebug 对 `case_001-005/014` 主要用于缩小信号和模块范围，真正的注错表达式仍需模型
   读取 RTL 后找到。GPT 全部成功；Qwen 在 `case_002/005/014` 已接近或得到正确根因，
   但 diff 持续无法应用。
5. `case_011-013` 是环境问题。KDebug 的静态 driver 结果只能佐证“Difftest/目标 RTL
   没有正常生效”，决定性线索仍来自 run log、配置文件和 judge 目标。
6. `case_010/016` 存在严重 benchmark 语义错误：实际 RTL 与 `case_006` 完全相同，
   都是 `Alu_3.sv` 的延迟 LSB 翻转；公开标签和 KDebug plan 却把模型引向 Cache/LSU 的
   `NewLoadUnit.sv`。两个模型在这两项都未访问真正注错文件，因此这些 TIMEOUT 不能用于
   评价 Cache/MMU 或 LSU 调试能力。
7. Qwen 的主要失败不是完全看不出根因，而是补丁落地循环失控。典型重复次数为：
   `case_002` 460 次、`case_005` 618 次、`case_009` 340 次、`case_016` 250 次。
   这些任务在 3600 秒预算内反复输出相同、不可应用的 diff，没有进入有效 build/run。

本轮没有运行 `without_kdebug` 对照组，因此本文只能根据 transcript 内的证据使用链判断
KDebug 是否参与定位。第 4 节在每个 case 内逐模型对照本轮工具思路、历史无工具思路、
终态、耗时与迭代，第 10 节给出整体汇总；这些数据只能用于观察，不能把 PASS 率或耗时
差异解释成严格的工具因果增益。

## 2. 最新结果

| 模型 | 任务 | PASS | TIMEOUT | PASS 率 | 累计耗时 | 累计迭代 | 累计 token |
|---|---:|---:|---:|---:|---:|---:|---:|
| GPT-5.5 | 16 | 14 | 2 | 87.5% | 11,479.833s | 83 | 2,127,367 |
| Qwen3.6-35B | 16 | 6 | 10 | 37.5% | 36,725.953s | 3,369 | 111,419,637 |
| 合计 | 32 | 20 | 12 | 62.5% | 48,205.786s | 3,452 | 113,547,004 |

| Case | GPT-5.5 | Qwen3.6-35B | 实际注错类别 |
|---|---|---|---|
| `case_001` | PASS, 30.961s, 1 iter | PASS, 50.628s, 2 iter | 多 beat AW 地址 bit 3 翻转 |
| `case_002` | PASS, 35.789s, 1 iter | TIMEOUT, 464 iter | 四 beat error response 被改成 OK |
| `case_003` | PASS, 28.261s, 1 iter | PASS, 73.124s, 1 iter | 非首 beat 清除 `strb[0]` |
| `case_004` | PASS, 25.893s, 1 iter | PASS, 350.293s, 2 iter | `0x1bad_0000` 被误解码为 UART |
| `case_005` | PASS, 36.011s, 1 iter | TIMEOUT, 620 iter | `T_ERR && addr_q[5]` 时返回 OK |
| `case_006` | PASS, 2650.923s, 2 iter | TIMEOUT, 436 iter | `issueTime > 5000` 后 ALU result LSB 翻转 |
| `case_007` | PASS, 205.795s, 2 iter | TIMEOUT, 142 iter | `issueTime > 1000` 后吞掉 `rfWen` |
| `case_008` | PASS, 212.067s, 2 iter | PASS, 224.138s, 2 iter | 有效整数 load data LSB 翻转 |
| `case_009` | PASS, 261.057s, 2 iter | TIMEOUT, 343 iter | redirect target bit 1 翻转 |
| `case_010` | TIMEOUT, 3600s, 32 iter | TIMEOUT, 3599.574s, 272 iter | 实际与 `case_006` 相同，标签和 evidence 错位 |
| `case_011` | PASS, 49.820s, 1 iter | TIMEOUT, 488 iter | Difftest 运行环境/参考模型加载异常 |
| `case_012` | PASS, 41.625s, 2 iter | PASS, 21.179s, 1 iter | 运行了错误 UVM case |
| `case_013` | PASS, 13.016s, 1 iter | PASS, 9.830s, 1 iter | stale simv 替代真实 simv |
| `case_014` | PASS, 31.076s, 1 iter | TIMEOUT, 3599.280s, 112 iter | `case_003` RTL + wrong case dispatch |
| `case_015` | PASS, 657.539s, 4 iter | TIMEOUT, 3599.274s, 229 iter | `case_009` RTL + Difftest 环境错误 |
| `case_016` | TIMEOUT, 3600s, 29 iter | TIMEOUT, 3599.124s, 254 iter | `case_006` RTL + `RUN_TIMEOUT_SEC=1` |

## 3. 工具作用判定标准

本文对每个模型单独判断工具作用，不用 `tool_evidence_valid` 代替效果判断。

| 等级 | 含义 |
|---|---|
| A：决定性 | KDebug 直接暴露注错常量、条件、driver、文件和行号，并形成成功补丁 |
| B：实质缩小范围 | KDebug 指向正确模块/信号链，模型还需读代码找真正注错表达式 |
| C：佐证 | KDebug 只证明目标信号未活动或结构驱动正常，根因主要来自日志/配置 |
| D：有证据但未有效利用 | 证据足够或接近足够，但模型改错文件、造错上下文或无法落地 |
| E：采集目标错误 | KDebug 命令执行和输出都有效，但 benchmark plan 选错了信号，证据误导模型 |

## 4. 逐 Case 分析

本节中的“使用 KDebug 思路”来自最新工具组 transcript、manifest 和 `evidence_used`；
“不使用 KDebug 思路”来自历史 `without_kdebug` transcript、patch 记录和运行反馈，而不是
根据终态反推。两轮的 runner、API 状态和执行日期并不完全相同，因此“提升”同时报告终态、
耗时、迭代和定位路径，只把能够由逐步记录支持的变化归因到 KDebug。

### 4.1 `case_001`：多 beat AW 地址 bit 3 翻转

**实际注错**：`rtl/xs_generated_rtl_bridge.sv` 在 `beats_q > 1` 时把
`addr_q[30:0]` 改成 `addr_q[30:0] ^ 31'h8`，导致 burst 写地址偏移 8 byte。

**KDebug 证据**：`kdebug_handshake_window.json` 对 `xs_bench_tb.dut.addr_q` 做
`trace.driver`，得到 `bus.req_addr -> addr_q`。它证明请求地址进入 bridge 时未损坏，
但没有直接追到后面的 AW 端口 XOR。

**模型证据与无工具对照**：

| 模型 | 本轮实际使用的 KDebug 证据 | 本轮 `with_kdebug` | 历史 `without_kdebug` | 逐 case 观察 |
|---|---|---:|---:|---|
| GPT-5.5 | 用 `addr_q <- bus.req_addr` 排除上游损坏，转查下游 AW 地址变换。 | PASS, 30.961s, 1 iter | PASS, 22.338s, 1 iter | 同为 PASS。 |
| Qwen3.6-35B | 引用同一 driver 与 data mismatch，找到 AW 地址 XOR，并结合 VCS 语法反馈修正补丁。 | PASS, 50.628s, 2 iter | PASS, 16.205s, 1 iter | 同为 PASS。 |

**GPT-5.5 使用 KDebug 的思路与结果**：模型把 scoreboard 的 burst read mismatch 与地址链结合，检查
bridge 下游端口后直接发现条件 XOR。首轮把
`.auto_in_aw_bits_addr((beats_q > 1) ? addr_q ^ 8 : addr_q)` 改回
`.auto_in_aw_bits_addr(addr_q)`，一次 build/run/judge 即 PASS。

**GPT-5.5 历史不使用 KDebug 的思路**：直接阅读 fail log 和允许范围内的 bridge RTL，
从多 beat 才出现地址偏移这一条件定位到 AW 地址上的 `beats_q > 1` 与 XOR 8，首个响应就
给出同一单行修复并 PASS；没有先做 driver 排除。

**Qwen3.6-35B 使用 KDebug 的思路与结果**：首轮也发现 XOR，但在修改 AW 时顺带去掉 AW/AR named-port
连接的括号，VCS 报 `token is 'addr_q'`。第二轮依据 build log 恢复括号，同时保留取消
XOR 的修改，随后 PASS。

**Qwen3.6-35B 历史不使用 KDebug 的思路**：从 burst readback mismatch 和可见 RTL 直接
解释 XOR 8 如何把多 beat 写请求送到错误地址，一轮删除条件变换并 PASS，未经历本轮的
named-port 语法回归。

**有/无工具提升分析**：两模型的工具作用等级均为 **B**，因为 driver 证据能排除上游，
但实际注错仍靠代码审查发现。终态没有提升，GPT 同为 1 iter 且工具组慢 8.623 秒；Qwen
从无工具 1 iter/16.205 秒变为工具组 2 iter/50.628 秒。此 case 的 KDebug 提升体现在证据
可审计性和搜索边界，而不是成功率或速度。

### 4.2 `case_002`：四 beat error response 被伪装成 OK

**实际注错**：B/R response 两处增加
`(sel_err && beats_q == 8'd4) ? XS_ST_OK : ...`，把四 beat error transaction 的
`SLVERR` 覆盖为 `OK`。

**KDebug 证据**：`kdebug_first_bad_beat.json` 追踪 `status_q`，得到默认
`XS_ST_OK` 和 `select_status(...)` 两个 driver。证据指向状态生成链，但注错位于
`status_q` 之后的最终 response mux。

**模型证据与无工具对照**：

| 模型 | 本轮实际使用的 KDebug 证据 | 本轮 `with_kdebug` | 历史 `without_kdebug` | 逐 case 观察 |
|---|---|---:|---:|---|
| GPT-5.5 | 以 status driver 为入口，结合 `got=0, exp=2` 转查 B/R mux，识别四 beat 强制 OK。 | PASS, 35.789s, 1 iter | PASS, 214.690s, 7 iter | 同为 PASS；本轮少 6 iter。 |
| Qwen3.6-35B | 已从同一 status path 指出 `sel_err && beats_q==4` 强制 OK，但 diff 上下文始终未匹配。 | TIMEOUT, 3600s, 464 iter | TIMEOUT, 3605.724s, 447 iter | 同为 TIMEOUT。 |

**GPT-5.5 使用 KDebug 的思路与结果**：从 `got=0, exp=2` 推断错误状态被吞，继续检查 S_B/S_R，
一次性删除两处四 beat 特判，首轮 PASS。

**GPT-5.5 历史不使用 KDebug 的思路**：仅靠 mismatch 和 RTL 也在第一次响应识别 B/R
两处 `sel_err && beats_q==4` 特判，随后连续调整 unified diff 的行号和上下文；第 7 轮补丁
才应用并 PASS。定位本身正确，时间主要耗在补丁落地。

**Qwen3.6-35B 使用 KDebug 的思路与结果**：第 4 轮前已准确说明 `sel_err && beats_q==4` 强制 OK，
修复意图与 GPT 相同。但 diff 的 hunk 位置和上下文始终不匹配实际文件，464 次 patch
全部失败，未进入一次 build；其中最后 460 次响应完全相同，预算耗尽后 TIMEOUT。

**Qwen3.6-35B 历史不使用 KDebug 的思路**：由 `got=0, exp=2` 先判断 error status 被
错误覆盖，随后也锁定 B/R mux 中的四 beat 强制 OK；但反复生成与实际文件不匹配的相同
diff，447 轮后 TIMEOUT。

**有/无工具提升分析**：GPT 为 **B**，工具组从 7 iter/214.690 秒降为 1 iter/35.789 秒，
观察到少 6 轮、快 178.901 秒；KDebug 的 status driver 使其更快进入最终 mux。Qwen 为
**D**，两组都已诊断正确且都因 apply 失败 TIMEOUT，工具组还多 17 轮，因此没有终态提升；
瓶颈是补丁协议，不是 RTL 定位。

### 4.3 `case_003`：非首 beat 清除 byte lane 0

**实际注错**：`AXI4RAM.auto_in_w_bits_strb` 在 `beat_idx_q != 0` 时使用
`eff_mask_q & 8'hfe`，使第二个及后续 beat 的 byte lane 0 永远不写。

**KDebug 证据**：`kdebug_data_mismatch.json` 追踪 `eff_mask_q`，得到 `mask_q`、`8'h00`
和 `8'hff` driver。它表明 mask 正常形成，但没有直接指出 RAM 端口又清除了 bit 0。

**模型证据与无工具对照**：

| 模型 | 本轮实际使用的 KDebug 证据 | 本轮 `with_kdebug` | 历史 `without_kdebug` | 逐 case 观察 |
|---|---|---:|---:|---|
| GPT-5.5 | 用正常的 `eff_mask_q` driver 把检查点推进到下游 W strobe，找到 `& 8'hfe`。 | PASS, 28.261s, 1 iter | PASS, 20.821s, 1 iter | 同为 PASS。 |
| Qwen3.6-35B | 同样把 mask driver 与 write path 关联，定位并删除下游 `& 8'hfe`。 | PASS, 73.124s, 1 iter | TIMEOUT, 3602s, 209 iter | **终态改善**。 |

**GPT-5.5 使用 KDebug 的思路与结果**：把读回 mismatch 与非首 beat 的 W strobe 连接起来，删除
`beat_idx_q` 条件，恢复直接传递 `eff_mask_q`，首轮 PASS。

**GPT-5.5 历史不使用 KDebug 的思路**：从“多 beat 读回时 lane 0 为旧值/零”直接提出
非首 beat 写 strobe 丢位假设，检查 RAM 的 W 端口后删除 `& 8'hfe`，同样一轮 PASS。

**Qwen3.6-35B 使用 KDebug 的思路与结果**：先检查写路径、读路径和 XOR 聚合，最终同样锁定
`auto_in_w_bits_strb` 的 `& 8'hfe`，首轮给出相同单行修复并 PASS。

**Qwen3.6-35B 历史不使用 KDebug 的思路**：最初把全零 readback 解释为 RAM read-data
端口未连接，随后在 `AXI4RAM` 和 bridge 的 B/R 端口方向、连线名称间反复猜测；没有把
“仅非首 beat/lane 0”转成 W strobe 检查，209 轮后 TIMEOUT。

**有/无工具提升分析**：两模型均为 **B**。GPT 本来就能从症状直接定位，工具组同为
1 iter 且慢 7.440 秒，主要增加了可复核证据。Qwen 则从无工具 TIMEOUT 变为 73.124 秒
一轮 PASS，属于明确终态提升；`eff_mask_q` driver 把它从错误的 read-port 假设拉回真正的
write-mask 下游。

### 4.4 `case_004`：伪造地址页被误解码为 UART

**实际注错**：`is_uart_addr()` 除正常 `XS_UART_BASE` 外，又把整个
`0x1bad_0000` 页判为 UART，导致本应返回 `SLVERR` 的 unmapped 访问被路由到 UART。

**KDebug 证据**：`kdebug_decode_observation.json` 追踪 `sel_uart`，得到
`target_q -> sel_uart`，把问题定位到 target/decode 链。

**模型证据与无工具对照**：

| 模型 | 本轮实际使用的 KDebug 证据 | 本轮 `with_kdebug` | 历史 `without_kdebug` | 逐 case 观察 |
|---|---|---:|---:|---|
| GPT-5.5 | 沿 `target_q -> sel_uart` 回查 decode function，找到 `0x1bad_xxxx` 伪 UART 页。 | PASS, 25.893s, 1 iter | PASS, 432.426s, 28 iter | 同为 PASS；本轮少 27 iter。 |
| Qwen3.6-35B | 用该 trace 判断失败地址被错误路由到 `T_UART`，API 重试后完成单行修复。 | PASS, 350.293s, 2 iter | PASS, 18.279s, 1 iter | 同为 PASS。 |

**GPT-5.5 使用 KDebug 的思路与结果**：根据失败地址 `0x1bad_xxxx` 反查 `is_uart_addr()`，删除伪造地址
匹配，一轮 PASS。

**GPT-5.5 历史不使用 KDebug 的思路**：从 `periph_unmapped got=0, exp=2` 和失败地址页
直接检查 decode function，第一轮已给出删除 `0x1bad_0000` 匹配的正确补丁；但历史 runner
连续拒绝 diff 上下文，直到第 28 轮才落地 PASS。

**Qwen3.6-35B 使用 KDebug 的思路与结果**：第一次运行已诊断正确，但输出的 diff 没有形成有效改动，
build/run/judge 仍失败；随后 API 调用超时，该目录按 `RETRY_LATER` 归档。重试时再次得到
同一根因，输出精确单行补丁并 PASS。最终 350.293 秒包含前一次 300 秒 API 等待。

**Qwen3.6-35B 历史不使用 KDebug 的思路**：直接把 `0x1bad_xxxx` 被错误返回 OK 解释为
unmapped 地址误入 UART target，在 `is_uart_addr()` 中看到额外地址页后做单行删除，1 iter
即 PASS。

**有/无工具提升分析**：两模型均为 **B**。GPT 从 28 iter/432.426 秒降到 1 iter/
25.893 秒，搜索与落地显著收敛；Qwen 则无工具更快，本轮工具组的 350.293 秒主要来自
300 秒 API 等待，并非 trace 计算成本。KDebug 对根因不是决定性的，因为失败地址和函数
常量本身已经足够直接。

### 4.5 `case_005`：地址 bit 5 条件性吞掉 error status

**实际注错**：B/R response 两处增加
`(target_q == T_ERR) && addr_q[5] ? XS_ST_OK : ...`，导致一半特定 unmapped 地址返回 OK。

**KDebug 证据**：`kdebug_response_order.json` 与 `case_002` 类似，只追到 `status_q` 的
`select_status(...)` driver；真正覆盖发生在最终 response mux。

**模型证据与无工具对照**：

| 模型 | 本轮实际使用的 KDebug 证据 | 本轮 `with_kdebug` | 历史 `without_kdebug` | 逐 case 观察 |
|---|---|---:|---:|---|
| GPT-5.5 | 从 `status_q <- select_status(...)` 继续检查 response mux，识别 `addr_q[5]` 条件覆盖。 | PASS, 36.011s, 1 iter | PASS, 69.985s, 2 iter | 同为 PASS；本轮少 1 iter。 |
| Qwen3.6-35B | 已准确指出 `addr_q[5]` 吞掉 `SLVERR`，但 620 轮 patch 均未应用。 | TIMEOUT, 3600s, 620 iter | TIMEOUT, 3600s, 220 iter | 同为 TIMEOUT。 |

**GPT-5.5 使用 KDebug 的思路与结果**：从失败地址均带 `addr_q[5]=1` 识别条件性覆盖，删除 B/R 两处
特判，首轮 PASS。

**GPT-5.5 历史不使用 KDebug 的思路**：直接比较通过/失败地址的 bit 5，并在 S_B/S_R
response expression 中找到条件性 `XS_ST_OK`；首个 patch 上下文未匹配，第二轮精简后
PASS。

**Qwen3.6-35B 使用 KDebug 的思路与结果**：第一轮就指出 `addr_q[5]` 使 `SLVERR` 变成 `OK`，补丁意图
正确；但 620 次 patch 全部未应用，最后 618 次响应完全重复，没有 build/run，TIMEOUT。

**Qwen3.6-35B 历史不使用 KDebug 的思路**：先把 status 2 的语义和 `select_target`/
`select_status` 映射混在一起，之后才注意 response mux 中 `target_q==T_ERR && addr_q[5]`
强制 OK；虽然最终修复意图正确，220 轮 diff 仍未落地。

**有/无工具提升分析**：GPT 为 **B**，工具组少 1 iter、快 33.974 秒，status driver
帮助它更快把问题限定在 mux 后覆盖。Qwen 为 **D**；KDebug 让正确根因在第一轮出现，
属于定位提升，但两组终态均 TIMEOUT，且工具组重复 620 轮，说明 apply 机制完全抵消了
定位收益。

### 4.6 `case_006`：延迟触发的 ALU result LSB 翻转

**实际注错**：`rtl/Alu_3.sv` 在
`io_in_bits_perfDebugInfo_issueTime > 64'h1388` 后输出 `_T_0 ^ 1`。

**KDebug 证据**：`kdebug_commit_window.json` 直接给出四个 driver：常量 `1`、常量
`0x1388`、`_T_0`（`Alu_3.sv`）和 `issueTime`（`Alu_3.sv`）。这是本轮最完整的证据之一，
几乎等价于把注错表达式拆解出来。

**模型证据与无工具对照**：

| 模型 | 本轮实际使用的 KDebug 证据 | 本轮 `with_kdebug` | 历史 `without_kdebug` | 逐 case 观察 |
|---|---|---:|---:|---|
| GPT-5.5 | 直接采用 `Alu_3.sv`、常量 1、`0x1388`、`_T_0` 和 `issueTime`，恢复 ALU result 直通。 | PASS, 2650.923s, 2 iter | TIMEOUT, 9395.394s, 74 iter | **终态改善**。 |
| Qwen3.6-35B | 反复引用 `1/0x1388/issueTime`，但把证据套入不存在的端口和 assignment 上下文。 | TIMEOUT, 3599.509s, 436 iter | TIMEOUT, 3599.572s, 20 iter | 同为 TIMEOUT。 |

**GPT-5.5 使用 KDebug 的思路与结果**：第一轮依据 evidence 请求 `rtl/Alu_3.sv`；拿到文件后删除
`issueTime` 条件和 XOR，恢复 `assign io_out_bits_res_data = _T_0`。build 和 fullchip run
耗时较长，但一次闭环即 PASS。

**GPT-5.5 历史不使用 KDebug 的思路**：从寄存器 mismatch 猜测整数 ALU 运算、结果选择
或 bypass 数据错误，依次检查/修改 `AluDataModule`、`MiscResultSelect`、`BypassNetwork`，
还一度转向 UART 路径。累计 74 轮都未把症状与 `issueTime` 条件联系起来，未定位真正的
`Alu_3.sv` 输出 XOR，最终 TIMEOUT。

**Qwen3.6-35B 使用 KDebug 的思路与结果**：第一次归档尝试误改 ALU 内部 `_T_4` 的 OR/XOR，patch 未
应用后又遇到 API 超时。重启后虽然反复复述 evidence 中的 `1/0x1388/issueTime`，却持续
假设不存在的 module port 和 assignment 结构；435 次 patch 均未应用，无 build，TIMEOUT。

**Qwen3.6-35B 历史不使用 KDebug 的思路**：围绕 `a5 right=0, wrong=1` 反复解码失败 PC
附近指令，把问题猜成普通 ALU、AMO ALU、bypass 或 commit/register 语义错误，最终主要
尝试修改 `AMOALU.sv`；20 轮内没有发现延迟阈值和 `Alu_3.sv` 注错，TIMEOUT。

**有/无工具提升分析**：GPT 为 **A**，从 74 iter/TIMEOUT 变为 2 iter/PASS，KDebug
直接把错误文件、阈值、条件信号和 XOR 常量交给模型，改变了终态。Qwen 为 **D**：相比
无工具的错误 AMO/ALU 搜索，工具组已经准确复述真实表达式，定位质量显著提升；但无法把
证据转换成匹配生成 RTL 的 diff，故终态仍为 TIMEOUT，且迭代数升至 436。

### 4.7 `case_007`：延迟吞掉 `rfWen`

**实际注错**：`Alu_3.sv` 在 `issueTime > 0x3e8` 且原始 `rfWen=1` 时强制输出 0。

**KDebug 证据**：`kdebug_control_first_divergence.json` 对 `io_out_bits_ctrl_rfWen` 给出
常量 `0`、常量 `0x3e8`、原始 `rfWen` 和 `issueTime`，并标出 `Alu_3.sv` 行号。

**模型证据与无工具对照**：

| 模型 | 本轮实际使用的 KDebug 证据 | 本轮 `with_kdebug` | 历史 `without_kdebug` | 逐 case 观察 |
|---|---|---:|---:|---|
| GPT-5.5 | 直接采用 `0/0x3e8/rfWen/issueTime/Alu_3.sv`，移除 timestamp 对 `rfWen` 的控制。 | PASS, 205.795s, 2 iter | TIMEOUT, 3603.448s, 17 iter | **终态改善**。 |
| Qwen3.6-35B | 正确解释 timestamp 不应控制 architectural write enable，但补丁混入虚构上下文。 | TIMEOUT, 3600s, 142 iter | TIMEOUT, 3601.631s, 243 iter | 同为 TIMEOUT。 |

**GPT-5.5 使用 KDebug 的思路与结果**：第一轮请求 `Alu_3.sv`，第二轮把条件表达式恢复成直接传递
`io_in_bits_ctrlPipe_0_rfWen`，PASS。

**GPT-5.5 历史不使用 KDebug 的思路**：根据 fail log 中的 register-cache assertion 和
随机样式寄存器值，优先假设物理寄存器/RegCache 同周期读写 bypass 返回陈旧数据，请求并
修改 `RegCacheDataModule.sv`；17 轮后仍未检查 `Alu_3.sv` 的 `rfWen` 输出条件，TIMEOUT。

**Qwen3.6-35B 使用 KDebug 的思路与结果**：从第一轮起就正确指出 performance timestamp 不应驱动
architectural write enable，但构造的 diff 混入虚构 module、`...` 占位和无关 AXI
端口上下文。142 次全部 apply 失败，最后 134 次响应相同，未 build，TIMEOUT。

**Qwen3.6-35B 历史不使用 KDebug 的思路**：从寄存器状态发散和 RegCache assertion 出发，
在 `RegCacheDataModule`、`RegFile`、`Backend`、`Commit` 等模块间搜索 stale/uninitialized
数据或错误 writeback，没有形成“延迟后吞掉 `rfWen`”假设；243 轮后 TIMEOUT。

**有/无工具提升分析**：GPT 为 **A**，从 17 iter/TIMEOUT 变为 2 iter/205.795 秒 PASS，
属于明确终态提升。Qwen 为 **D**：KDebug 把搜索从宽泛寄存器链收敛到 `Alu_3.sv` 的
timestamp/`rfWen` 条件，并把迭代从 243 降到 142，但补丁格式仍阻止成功，因此只有诊断
和搜索效率提升，没有终态提升。

### 4.8 `case_008`：有效整数 load data LSB 翻转

**实际注错**：`NewLoadUnit.sv` 在 `io_ldout_toIntRf_valid` 时把
`_dataPath_io_s3ShiftAndExtData[63:0]` XOR 1。

**KDebug 证据**：`kdebug_lsu_first_bad_load.json` 同时列出常量 `1`、load data part-select
和 `io_ldout_toIntRf_valid`，并定位 `NewLoadUnit.sv:758`。

**模型证据与无工具对照**：

| 模型 | 本轮实际使用的 KDebug 证据 | 本轮 `with_kdebug` | 历史 `without_kdebug` | 逐 case 观察 |
|---|---|---:|---:|---|
| GPT-5.5 | 直接采用常量 1、load valid、shift/extend data 和 `NewLoadUnit.sv:758`，删除 XOR。 | PASS, 212.067s, 2 iter | TIMEOUT, 3599.911s, 37 iter | **终态改善**。 |
| Qwen3.6-35B | 将同一 driver 与 `0x1a -> 0x1b` 对应，读取目标 assignment 后完成修复。 | PASS, 224.138s, 2 iter | TIMEOUT, 3614.927s, 177 iter | **终态改善**。 |

**GPT-5.5 使用 KDebug 的思路与结果**：先从首个 bad load 请求 `NewLoadUnit.sv`，随后删除 ternary/XOR，
恢复直接 load writeback，PASS。

**GPT-5.5 历史不使用 KDebug 的思路**：虽然从 `0x1a -> 0x1b` 看出相邻 byte/LSB 特征，
但把根因放在 load byte-lane、地址 offset、DCache/uncached response 和 `AXI4Flash`，最终
给 flash 窄读地址加补偿；37 轮未触及 `NewLoadUnit` 最终 writeback XOR，TIMEOUT。

**Qwen3.6-35B 使用 KDebug 的思路与结果**：第一轮根据 `0x1a -> 0x1b` 识别 LSB 翻转，并修正了自己对
指令的解码为 `LWU`；请求文件后在第二轮看到准确 assignment，给出与 GPT 相同补丁，PASS。

**Qwen3.6-35B 历史不使用 KDebug 的思路**：起初把失败指令误解为 `addi`，围绕 ALU、
AMOALU、bypass 和寄存器源值推理；之后虽重新识别为 load，仍继续猜测通用数据通路，
没有定位 `NewLoadUnit` 的 valid 条件 XOR，177 轮后 TIMEOUT。

**有/无工具提升分析**：两模型均为 **A**。GPT 从 37 iter/TIMEOUT 变为 2 iter/
212.067 秒 PASS，Qwen 从 177 iter/TIMEOUT 变为 2 iter/224.138 秒 PASS。KDebug 不只是
缩小范围，而是直接提供 `NewLoadUnit.sv:758`、常量 1、load-valid 与 data part-select，
同时纠正了两模型各自的 AXIFlash/ALU 错误假设，是本轮最清晰的双模型终态提升。

### 4.9 `case_009`：redirect target bit 1 翻转

**实际注错**：`BranchUnit.sv` 在 redirect valid 时，对 short target 和 full target 都
XOR 常量 2，使跳转目标偏移一个 16-bit 半字。

**KDebug 证据**：`kdebug_redirect_pc_divergence.json` 直接给出常量 `2`、
`_addModule_io_target`、`redirect_valid` 和 `BranchUnit.sv` 行号。

**模型证据与无工具对照**：

| 模型 | 本轮实际使用的 KDebug 证据 | 本轮 `with_kdebug` | 历史 `without_kdebug` | 逐 case 观察 |
|---|---|---:|---:|---|
| GPT-5.5 | 直接采用常量 2、target、redirect valid 和 `BranchUnit.sv` 行号，删除两处 XOR。 | PASS, 261.057s, 2 iter | PASS, 278.159s, 2 iter | 同为 PASS。 |
| Qwen3.6-35B | 看到了 redirect 异常，却没有优先处理 BranchUnit 常量 2，转而修改普通加法模块。 | TIMEOUT, 3600s, 343 iter | TIMEOUT, 3608.197s, 260 iter | 同为 TIMEOUT。 |

**GPT-5.5 使用 KDebug 的思路与结果**：第一轮请求 `BranchUnit.sv`，第二轮同时恢复 short/full target
为 `_addModule_io_target`，fullchip PASS。

**GPT-5.5 历史不使用 KDebug 的思路**：从异常 PC 相差一个 16-bit halfword 推断 branch
redirect target 偏移，主动请求 `BranchUnit.sv`，看到 short/full target 的 XOR 2 后两处
同时恢复，2 iter/278.159 秒 PASS。

**Qwen3.6-35B 使用 KDebug 的思路与结果**：能判断异常 PC 来自错误 redirect，但把根因归到
`rtl/AddModule.sv`，反复把普通加法改成 signed 加法。这既没有处理 evidence 中明确出现的
常量 2，也没有修改 `BranchUnit.sv`。343 次 apply 失败，其中 340 次响应相同，TIMEOUT。

**Qwen3.6-35B 历史不使用 KDebug 的思路**：能从异常取指/illegal instruction 推断
redirect 方向，但在 `Bpu`、`AheadBtb`、`BranchModule`、`BranchUnit` 等预测和重定向模块
间广泛猜测，未形成可应用的 XOR 2 修复，260 轮后 TIMEOUT。

**有/无工具提升分析**：GPT 为 **A**，两组均为 2 iter/PASS，工具组仅快 17.102 秒；
无工具日志本身已经暴露 halfword 偏移，所以主要提升是把 XOR 2 变成直接、可审计的 driver
证据。Qwen 为 **D**：证据比无工具搜索明确得多，但模型反而忽略 `BranchUnit` 常量 2，
两组都 TIMEOUT，说明“提供证据”不等于“模型会优先采用证据”。

### 4.10 `case_010`：标签和 evidence 错位的重复 ALU 注错

**实际注错**：VM 实测 SHA-256 证明 `case_010/rtl/Alu_3.sv` 与 `case_006` 完全相同：
`e9cf561719217c46dcdc511ea3d1870c48479053baf42c4ac2b594b02b21f8d2`。真实问题仍是
`issueTime > 5000` 后 ALU result XOR 1，并不是公开标签所称的 Cache/MMU/refill 问题。

**KDebug 证据**：`kdebug_tlb_cache_refill.json` 实际只对
`NewLoadUnit.io_ldout_toIntRf_bits_data` 做 driver trace，得到未注错的
`_dataPath_io_s3ShiftAndExtData[63:0]`。文件名虽称 TLB/cache/refill，内容没有这些链路，
且完全没有追踪真正注错的 `Alu_3`。

**模型证据与无工具对照**：

| 模型 | 本轮实际使用的 KDebug 证据 | 本轮 `with_kdebug` | 历史 `without_kdebug` | 逐 case 观察 |
|---|---|---:|---:|---|
| GPT-5.5 | 按错误的 NewLoadUnit driver 证据检查 LoadUnit、DMAC、UART 和 bypass，从未检查实际注错的 `Alu_3.sv`。 | TIMEOUT, 3600s, 32 iter | TIMEOUT, 3687.995s, 11 iter | 同为 TIMEOUT。 |
| Qwen3.6-35B | 被同一错误证据锚定到 NewLoadUnit，并反复构造不存在的 Scala/Chisel 上下文。 | TIMEOUT, 3599.574s, 272 iter | TIMEOUT, 3599.250s, 177 iter | 同为 TIMEOUT。 |

**GPT-5.5 使用 KDebug 的思路与结果**：模型先沿 evidence 请求 `NewLoadUnit.sv`，随后依次尝试
`AXI4DMAC` 地址映射、`AXI4UART` status、`MiscResultSelect`、`AluDataModule` 和 bypass/load
hold 等假设。它进行了 21 次 patch 尝试、13 次 build、12 次 run/judge，反馈不断改变
症状并诱发新回归，但 32 轮中从未检查 `Alu_3.sv`，最终 TIMEOUT。

**GPT-5.5 历史不使用 KDebug 的思路**：受公开 Cache/MMU 标签和 polling mismatch 影响，
先检查 `AXI4UART`，之后也触及 `Alu.sv/Alu_3.sv`，但只围绕 PC 特判、result selection
等猜测修改，没有识别 `issueTime > 5000` 的 XOR；11 轮内修改 UART/ALU 后仍 TIMEOUT。

**Qwen3.6-35B 使用 KDebug 的思路与结果**：持续把 `NewLoadUnit` 当成根因，猜测不存在于生成 SV 的
Scala/Chisel 语句 `s3ShiftAndExtData := ...`。272 轮只有 11 种响应，大量重复同一不可应用
patch，未进入 build，TIMEOUT。

**Qwen3.6-35B 历史不使用 KDebug 的思路**：从同一寄存器 mismatch 反复解码失败指令，
把问题归到 `AMOALU`、普通 `Alu`、`AtomicsUnit` 或 Backend 数据通路，177 轮内没有发现
延迟阈值注错；虽未被 NewLoadUnit evidence 锚定，仍受错误 case 标签影响而 TIMEOUT。

**有/无工具提升分析**：两模型均为 **E**。两组终态都 TIMEOUT；工具组相对无工具还从
GPT 11 轮增至 32 轮、Qwen 177 轮增至 272 轮。错误 plan 把模型系统性固定在正常的
NewLoadUnit 输出上，没有提供提升，反而减少了偶然检查真实 `Alu_3.sv` 的机会。该 case
必须修正采集信号后重测，当前差异不能用于评价 Cache/MMU 或模型 RTL 调试能力。

### 4.11 `case_011`：Difftest 参考模型运行环境异常

**实际问题**：case 配置中 `DIFF_ARG=`，但本轮实际首个阻塞症状是 simv 报
`FATAL: $(NEMU_HOME) is not defined!`，即参考模型在 DUT 正常执行前未加载。

**KDebug 证据**：`kdebug_runtime_observation.json` 只显示 `tb_top.sim.difftest_exit` 由
常量 0 驱动。它能说明 Difftest exit 没有正常活动，但不能区分 NEMU_HOME、SO 路径、
plusarg 或 stale executable。

**模型证据与无工具对照**：

| 模型 | 本轮实际使用的 KDebug 证据 | 本轮 `with_kdebug` | 历史 `without_kdebug` | 逐 case 观察 |
|---|---|---:|---:|---|
| GPT-5.5 | 把 `difftest_exit=0` 当作未启动佐证，真正依据 run log 的 `NEMU_HOME` FATAL 修复环境。 | PASS, 49.820s, 1 iter | PASS, 295.059s, 10 iter | 同为 PASS；本轮少 9 iter。 |
| Qwen3.6-35B | 也用常量 0 佐证 Difftest 未启动并识别 `NEMU_HOME`，但目录和 symlink 补丁未正确落地。 | TIMEOUT, 3600s, 488 iter | PASS, 34.958s, 4 iter | **终态回退**。 |

**GPT-5.5 使用 KDebug 的思路与结果**：以 run log 的 FATAL 为主线，在 `scripts/run.sh` 创建 case-local
`NEMU_HOME`，并把现有 `REF_SO` 链接到 `$NEMU_HOME/build/riscv64-nemu-interpreter-so`。
最终 run log 明确输出 `Difftest enabled`、`HIT GOOD TRAP` 和 `DIFFTEST WORKLOAD DONE`，
首轮 PASS。它没有恢复 `DIFF_ARG`，而是满足了该 simv 的参考模型查找约定。

**GPT-5.5 历史不使用 KDebug 的思路**：完全以 `NEMU_HOME is not defined` run log 为
主线，反复尝试导出 `NEMU_HOME`、调整 `REF_SO` 定义顺序并创建 simv 期望的 build 子目录/
symlink；前几轮因路径和 shell `nounset` 问题失败，第 10 轮才 PASS。

**Qwen3.6-35B 使用 KDebug 的思路与结果**：同样识别 NEMU_HOME 缺失，但先把它直接设为
`ready-to-run`，使 simv 转而查找不存在或不可访问的 `ready-to-run/build/...so`。后续模型
已口头认识到需要 symlink，却反复输出 export `REF_SO` 或增加 `+REF_SO` 的不可应用补丁。
488 轮中 486 次 apply 失败，仅前两次进入 build/run，最终 TIMEOUT。

**Qwen3.6-35B 历史不使用 KDebug 的思路**：同样从 FATAL 直接识别 NEMU_HOME 缺失，
先修环境变量，再根据“`$NEMU_HOME/build/...so` 不存在”和变量定义顺序反馈修正目录/
symlink，4 iter/34.958 秒 PASS。

**有/无工具提升分析**：两模型均为 **C**，决定性线索始终是 run log。GPT 从 10 iter/
295.059 秒降为 1 iter/49.820 秒，KDebug 的 `difftest_exit=0` 提供阶段佐证，但不能单独解释
这 9 轮差异。Qwen 则从无工具 PASS 回退为工具组 TIMEOUT；两次都知道 NEMU_HOME 根因，
差异发生在路径构造和 patch apply，因此不能把回退归因成 KDebug 缺少信息。

### 4.12 `case_012`：运行错误的 UVM case

**实际注错**：`config/case.env` 把 `BENCH_CASE` 从目标
`ut_axi_burst_outstanding` 改成 `ut_axi_error_backpressure`。

**KDebug 证据**：`kdebug_runtime_observation.json` 只显示 `bus.req_addr -> addr_q`。
它是结构性 driver 证据，不能证明完整 RTL 功能正确，也不能直接指出 case dispatch。

**模型证据与无工具对照**：

| 模型 | 本轮实际使用的 KDebug 证据 | 本轮 `with_kdebug` | 历史 `without_kdebug` | 逐 case 观察 |
|---|---|---:|---:|---|
| GPT-5.5 | 仅用 `addr_q <- bus.req_addr` 排除明显 RTL 断线，根因来自 config、日志与 judge 对照。 | PASS, 41.625s, 2 iter | PASS, 37.196s, 2 iter | 同为 PASS。 |
| Qwen3.6-35B | 同样把结构 driver 当辅助证据，直接依据配置不一致修正 `BENCH_CASE`。 | PASS, 21.179s, 1 iter | PASS, 7.858s, 1 iter | 同为 PASS。 |

**GPT-5.5 使用 KDebug 的思路与结果**：比较 `case_meta`、judge 目标、run log 和 `config/case.env`，
判断运行 workload 错误。首个双文件 diff 格式未应用；第二轮同时修正 config 和 run.sh
默认值，PASS。

**GPT-5.5 历史不使用 KDebug 的思路**：直接对照 run log 中实际
`ut_axi_error_backpressure`、judge 期望的 `ut_axi_burst_outstanding` 和 `case.env`，首轮
已同时修改 config/run.sh，但 diff 格式未落地；第二轮精简上下文后 PASS。

**Qwen3.6-35B 使用 KDebug 的思路与结果**：直接比较 judge 期望和配置，认为仅改
`config/case.env` 已足够，一轮修正并 PASS。

**Qwen3.6-35B 历史不使用 KDebug 的思路**：从 run log 的 PASS case 名称与 judge 目标
不一致直接判断 dispatch 错误，只改 `config/case.env`，1 iter/7.858 秒 PASS。

**有/无工具提升分析**：两模型均为 **C**。有无工具的 GPT 都是 2 iter，Qwen 都是
1 iter，终态完全相同；工具组分别多 4.429 秒和 13.321 秒。`addr_q <- bus.req_addr` 只能
辅助排除结构断线，未改善该配置型 case 的定位或修复，真正证据是日志/config/judge 三方
不一致。

### 4.13 `case_013`：stale simv 制造假成功

**实际注错**：`config/run_target.env` 设置 `SIMV=./env/stale_simv`；该脚本只打印
“workload was not executed / DIFFTEST disabled”后返回 0。

**KDebug 证据**：`kdebug_runtime_observation.json` 同样只看到 `difftest_exit=0`，与
未执行真实 simulator 相符，但不直接识别 stale 路径。

**模型证据与无工具对照**：

| 模型 | 本轮实际使用的 KDebug 证据 | 本轮 `with_kdebug` | 历史 `without_kdebug` | 逐 case 观察 |
|---|---|---:|---:|---|
| GPT-5.5 | 用 `difftest_exit=0` 佐证 Difftest 未活动，再结合 stale simulator 日志与配置恢复真实 simv。 | PASS, 13.016s, 1 iter | PASS, 8.696s, 1 iter | 同为 PASS。 |
| Qwen3.6-35B | 使用相同佐证和日志/config 主线，完成同一单行路径修复。 | PASS, 9.830s, 1 iter | PASS, 6.215s, 1 iter | 同为 PASS。 |

**GPT-5.5 使用 KDebug 的思路与结果**：结合 fail log 的明确文本和 config，把 `SIMV` 改回 `./simv`，
13.016 秒一轮 PASS。

**GPT-5.5 历史不使用 KDebug 的思路**：看到 `stale simulator image selected` 和
`DIFFTEST disabled` 后直接检查 `config/run_target.env`，把 `SIMV=./env/stale_simv` 恢复为
`./simv`，1 iter/8.696 秒 PASS。

**Qwen3.6-35B 使用 KDebug 的思路与结果**：采用相同判断和单行修改，9.830 秒一轮 PASS。

**Qwen3.6-35B 历史不使用 KDebug 的思路**：沿 build 产物是 `./simv`、run 配置却选择
`./env/stale_simv` 的矛盾做同一单行修复，1 iter/6.215 秒 PASS。

**有/无工具提升分析**：两模型均为 **C**。终态和迭代数完全相同，工具组分别慢
4.320 秒和 3.615 秒；KDebug 只把“Difftest 未活动”结构化为证据，不能比日志中的 stale
提示更直接。这里的价值是审计留痕，不是定位或性能提升。

### 4.14 `case_014`：write mask RTL 错误 + wrong case dispatch

**实际注错**：RTL 与 `case_003` 完全相同，仍是非首 beat 清除 `strb[0]`；同时
`config/case.env` 把目标 `it_memory_mixed_burst` 改成 `ut_axi_error_backpressure`。

**KDebug 证据**：

- `kdebug_rtl_observation.json`：`eff_mask_q` 由 `mask_q/0/ff` 驱动，缩小到 write mask path。
- `kdebug_runtime_observation.json`：`addr_q` 由 `bus.req_addr` 驱动，只提供结构性地址证据。

**模型证据与无工具对照**：

| 模型 | 本轮实际使用的 KDebug 证据 | 本轮 `with_kdebug` | 历史 `without_kdebug` | 逐 case 观察 |
|---|---|---:|---:|---|
| GPT-5.5 | 采用 mask driver 复用 `case_003` 的 signal-to-port 推理；地址 trace 仅作结构佐证。 | PASS, 31.076s, 1 iter | PASS, 149.270s, 2 iter | 同为 PASS；本轮少 1 iter。 |
| Qwen3.6-35B | 先过度解读地址 trace 并错误缩窄 RAM 地址；重启后识别 mask 注错，但 diff 未应用。 | TIMEOUT, 3599.280s, 112 iter | TIMEOUT, 3610.974s, 298 iter | 同为 TIMEOUT。 |

**GPT-5.5 使用 KDebug 的思路与结果**：一次响应同时恢复 `BENCH_CASE=it_memory_mixed_burst` 和
`auto_in_w_bits_strb=eff_mask_q`，一次 build/run/judge PASS。RTL 定位复用了 `case_003`
相同的 signal-to-port 推理，环境问题来自 config/run 对照。

**GPT-5.5 历史不使用 KDebug 的思路**：从 judge/config 识别 wrong case dispatch，同时
从多 beat readback mismatch 检查 bridge 的 W strobe，首轮已提出恢复 BENCH_CASE 和删除
`& 8'hfe`；因双文件 diff 上下文问题，第 2 轮才应用并 PASS。

**Qwen3.6-35B 使用 KDebug 的思路与结果**：第一次尝试正确修 config，但过度解读地址 driver，错误地把
RAM 地址从 `addr_q[30:0]` 改成 `addr_q[18:3]`。该补丁成功 build/run，却产生 60 个 data
mismatch；随后 API 调用超时，目录按 RETRY_LATER 归档。重启后模型改为正确识别
`& 8'hfe` 和错误 BENCH_CASE，但接下来的 111 个 patch 全部无法应用，最后 108 次响应
相同，TIMEOUT。结果行中的两个 modified files 来自归档中的错误地址补丁，不代表最终
正确修复已经落地。

**Qwen3.6-35B 历史不使用 KDebug 的思路**：主要从全零 readback 猜测 RAM 数据端口、
地址/掩码连接和 testbench 行为；后续虽修改过 `case.env`、bridge 和 scoreboard 文件，
但没有稳定形成“wrong dispatch + 非首 beat `strb[0]`”的最小双修复，298 轮后 TIMEOUT。

**有/无工具提升分析**：GPT 的 RTL 部分为 **B**、环境部分为 **C**，从 2 iter/
149.270 秒降为 1 iter/31.076 秒，mask driver 对一次性双修复有实质帮助。Qwen 为 **D**：
工具组后期已说出两个正确根因，迭代也从 298 降为 112，但错误外推和 apply 失败使两组都
TIMEOUT；这是定位质量提升而非终态提升。

### 4.15 `case_015`：redirect target 错误 + Difftest 环境错误

**实际注错**：RTL 与 `case_009` 相同，redirect target XOR 2；环境中 `DIFF_ARG=`，使
参考模型启动参数缺失或依赖不完整。

**KDebug 证据**：

- `kdebug_rtl_observation.json` 直接给出常量 2、`_addModule_io_target`、redirect valid 和
  `BranchUnit.sv` 行号。
- `kdebug_runtime_observation.json` 只显示 `difftest_exit=0`。

**模型证据与无工具对照**：

| 模型 | 本轮实际使用的 KDebug 证据 | 本轮 `with_kdebug` | 历史 `without_kdebug` | 逐 case 观察 |
|---|---|---:|---:|---|
| GPT-5.5 | 用 BranchUnit 常量 2 证据修复 redirect RTL，再以 `difftest_exit=0` 和 run log 收敛环境。 | PASS, 657.539s, 4 iter | PASS, 276.202s, 3 iter | 同为 PASS。 |
| Qwen3.6-35B | 看到了常量 2、target、valid 和空 `DIFF_ARG`，但 RTL 与环境 diff 均未匹配真实文件。 | TIMEOUT, 3599.274s, 229 iter | TIMEOUT, 3599.476s, 467 iter | 同为 TIMEOUT。 |

**GPT-5.5 使用 KDebug 的思路与结果**：第一轮请求 `BranchUnit.sv`；第二轮同时删除 short/full target
两处 XOR，但顺带把 workload/ref 路径强制改成 `/root/...`，导致 FileReader 启动失败。
第三轮恢复 `/home/host/...` 优先路径；第四轮根据新的 `NEMU_HOME` FATAL 增加 NEMU_HOME
导出和默认 `+diff` 参数，最终 PASS。四轮体现了“RTL 根因先修好，环境反馈再逐步收敛”。

**GPT-5.5 历史不使用 KDebug 的思路**：从 illegal/misaligned PC 与正确 target 相差半字
推断 redirect 错误，先请求 `BranchModule` 再检查 `BranchUnit`，删除 target XOR 2；随后
根据 run feedback 修 `scripts/run.sh` 的参考模型环境，3 iter/276.202 秒 PASS。

**Qwen3.6-35B 使用 KDebug 的思路与结果**：能从 evidence 看到 BranchUnit 常量 2，也看到 `DIFF_ARG`
为空，但没有生成匹配真实 assignment 的补丁，反而猜测硬编码 `target=2`，环境修改也只是
把空值改成 `DIFF_ARG=""`。第一次 125 轮后遇到 API 502 归档；重试又执行 104 轮，仍无
一次有效 apply/build，累计 229 轮 TIMEOUT。

**Qwen3.6-35B 历史不使用 KDebug 的思路**：从异常 PC/branch trace 在 `Bpu`、
`AheadBtb`、`BranchModule`、`BranchUnit` 间搜索，同时注意到参考模型启动环境；但没有
稳定识别并应用 target XOR 2 与环境修复，467 轮后 TIMEOUT。

**有/无工具提升分析**：GPT 的 RTL 部分为 **A**、环境部分为 **C**。两组都 PASS，
但工具组因自行引入路径回归从 3 iter/276.202 秒变为 4 iter/657.539 秒，说明直接 RTL
证据未转化为端到端速度提升。Qwen 为 **D**：KDebug 把搜索明确到 BranchUnit 常量 2，并
将迭代从 467 降到 229，但 diff 仍未落地，只有定位/搜索效率提升，没有终态提升。

### 4.16 `case_016`：重复 ALU 注错 + 一秒运行超时

**实际注错**：`Alu_3.sv` 与 `case_006/010` SHA-256 完全相同，仍是延迟 LSB 翻转；
环境另加 `config/run.env: RUN_TIMEOUT_SEC=1`。公开标签声称 LSU/cache RTL 错误，与实际
文件不符。

**KDebug 证据**：

- `kdebug_rtl_observation.json` 错误地追踪未注错的 `NewLoadUnit` load output。
- `kdebug_runtime_observation.json` 只显示 `difftest_exit=0`，没有直接读取 timeout config。

**模型证据与无工具对照**：

| 模型 | 本轮实际使用的 KDebug 证据 | 本轮 `with_kdebug` | 历史 `without_kdebug` | 逐 case 观察 |
|---|---|---:|---:|---|
| GPT-5.5 | 被错误 NewLoadUnit evidence 引向 LoadUnit/DMAC；runtime 常量 0 也未直接暴露一秒 timeout。 | TIMEOUT, 3600s, 29 iter | TIMEOUT, 3601.672s, 14 iter | 同为 TIMEOUT。 |
| Qwen3.6-35B | 从配置而非 KDebug 修正一秒 timeout，但 RTL 仍被错误 evidence 锚定到 NewLoadUnit。 | TIMEOUT, 3599.124s, 254 iter | TIMEOUT, 3600s, 15 iter | 同为 TIMEOUT。 |

**GPT-5.5 使用 KDebug 的思路与结果**：沿错误 RTL evidence 先检查 `NewLoadUnit`，随后猜测 `AXI4DMAC`
byte/MMIO decode，再在 `NewLoadUnit` 上尝试清 bit 0、把值 1 强制改 0、按
`0x40600008` 特判等补丁；同时在 `/home/host` 与 `/root` workload 路径之间反复切换。
29 轮中有 26 次 patch、12 次 build/run，但没有一次通过 judge；模型既未打开
`Alu_3.sv`，也未直接修 `config/run.env`，最终 TIMEOUT，终态无有效修改。

**GPT-5.5 历史不使用 KDebug 的思路**：从配置直接看到一秒 timeout，并从 MMIO polling
处的 `a5=1/0` mismatch 猜测 UART/DMAC byte-lane 或 status decode；虽修改过
`config/run.env`、`AXI4DMAC` 和 `AXI4UART`，仍未检查真正注错的 `Alu_3.sv`，14 轮后
TIMEOUT。

**Qwen3.6-35B 使用 KDebug 的思路与结果**：模型正确发现 `RUN_TIMEOUT_SEC=1`，先后把它改为 3300/3600，
环境修改实际落地并完成 build/run/judge，但未解决 RTL。RTL 侧持续根据错误 evidence 猜测
`NewLoadUnit` 的 shift/extend 代码，253 轮中最后 250 次响应相同；API 502 后又有一次环境
重试并再次 API timeout。最终结果为 `env_only`，仍因实际 `Alu_3` 注错未修而 TIMEOUT。

**Qwen3.6-35B 历史不使用 KDebug 的思路**：同样先识别 `RUN_TIMEOUT_SEC=1`，之后把寄存器
mismatch 归因到 `AXI4UserYanker`、`SimTop` 或 load/MMIO 数据通路；15 轮内未发现
`Alu_3.sv` 的延迟 XOR，也没有形成最终有效修改，TIMEOUT。

**有/无工具提升分析**：RTL 对两模型均为 **E**，环境部分最多为 **C**。两组均 TIMEOUT；
工具组迭代反而从 GPT 14 增至 29、Qwen 15 增至 254。Qwen 工具组至少实际落地 timeout
配置，形成局部环境提升，但错误 NewLoadUnit plan 让两模型远离真实 Alu 注错，端到端没有
提升。有效 manifest 在这里仅证明调用合规，不能证明采集目标正确。

## 5. 跨 Case 模型行为

### 5.1 GPT-5.5

- 对 evidence 中出现的具体文件和常量利用率高。`case_006/007/008/009/015` 都先请求
  目标文件，再生成小范围补丁。
- 能利用 build/run/judge 反馈改变下一轮策略，`case_001/012/015` 的后续修改均针对真实
  编译或启动错误。
- 环境问题上更愿意审计脚本和运行约定，`case_011-013` 全部成功。
- 弱点是容易相信 benchmark 的信号选择。`case_010/016` 在 evidence 指错模块后产生大量
  合理但无关的局部假设，没有回到跨 case 哈希或注错模式做反证。
- `case_010/016` 也暴露了 speculative repair 风险：模型在没有确认注错差异时改动正常
  DMAC/UART/ALU/LoadUnit 逻辑，反馈被自己引入的回归污染。

### 5.2 Qwen3.6-35B

- 在 generated-wrapper 小 case 上具备有效分析能力，成功修复 `case_001/003/004`；在
  `case_008` 也能利用强 driver evidence 完成真实 fullchip RTL 修复。
- 环境文件非常明确时表现较好，`case_012/013` 都是一轮成功。
- 最主要问题是补丁协议稳定性。模型经常知道正确行，却使用不存在的上下文、Scala 语法、
  占位符或无关 module 内容，导致 `git apply` 和 tolerant apply 同时失败。
- runner 把同一 apply failure 继续反馈给模型后，模型常原样重发，不形成新的文件请求或
  更小 hunk，造成 10M 级 token 消耗和数百次无效迭代。
- 在 `case_009/015` 中，证据明确指向 BranchUnit 常量 2，模型仍修改 AddModule 或猜测
  assignment，说明它对 driver edge 中“source”和“最终注错表达式”的优先级处理不稳。
- API 300 秒超时和 502 造成了若干 `RETRY_LATER`，但并不是所有 TIMEOUT 的唯一原因。
  多数失败任务在 API 可用期间已经进入高重复、零 build 的补丁循环。

## 6. KDebug 的真实作用

### 6.1 明确起到决定性作用

- `case_006`：直接显示 `1/0x1388/issueTime/Alu_3`，决定 GPT 成功补丁。
- `case_007`：直接显示 `0/0x3e8/rfWen/issueTime/Alu_3`，决定 GPT 成功补丁。
- `case_008`：直接显示 `1/valid/NewLoadUnit:758`，两模型都成功。
- `case_009`：直接显示 `2/redirect_valid/BranchUnit`，决定 GPT 成功补丁。
- `case_015` RTL 部分：复现 `case_009` 的直接证据，决定 GPT 的 RTL 修复。

### 6.2 实质缩小搜索范围

- `case_001-005`：分别把搜索约束到 address、status、mask、decode、response path；注错
  位于 driver 之后的 port/mux/function，需要模型继续读代码。
- `case_014` RTL 部分：`eff_mask_q` trace 帮助回到 write strobe path。

### 6.3 只作佐证

- `case_011/013/015/016` 的 `difftest_exit=0` 不能区分多种环境根因。
- `case_012/014` 的 `bus.req_addr -> addr_q` 只能说明结构驱动关系，不能证明完整行为正确。
- 环境修复最终依赖 fail log、配置、文件路径和 judge 目标。

### 6.4 采集计划错误

- `case_010/016` 的实际注错都在 `Alu_3.sv`，但 plan 追踪 `NewLoadUnit`。
- KDebug 引擎没有返回伪造结果；它正确回答了错误问题。问题在 benchmark evidence plan
  与真实注错不一致。
- 后续重跑前应把两项 plan 改为追踪 `Alu_3.io_out_bits_res_data`，并在 manifest gate 中
  增加“目标文件必须与注错差异或首个异常链可达”的语义校验。

## 7. 对下一轮 Benchmark 的改进建议

1. 为每个 case 保存私有、机器可校验的 injected diff 哈希，并要求 evidence query 到达
   注错文件或由明确的 dependency path 连接到注错文件。
2. 在运行模型前做 case 去重检查。`case_006/010/016` 的 RTL 完全相同，不应以三个不同
   subsystem 标签计分。
3. runner 在同一响应连续 apply 失败 3 次后，应强制模型请求真实文件或自动提供目标文件
   精确上下文；不应允许 100 至 600 次原样重试。
4. 对 unified diff 做规范化：允许无行号的小 hunk、自动纠正生成 RTL 的空白差异，并在
   tolerant apply 后返回实际目标片段。
5. 环境 case 的 KDebug action 应补充独立 runtime audit action，输出 simv 路径、workload、
   NEMU_HOME、reference SO、plusarg 和 timeout 的结构化结果；静态 `trace.driver` 不足以
   诊断运行环境。
6. 报告中同时展示“定位是否正确”“补丁是否应用”“是否 build”“是否 run”“是否 PASS”，
   避免把 Qwen 这类正确定位但 apply 失败的任务简单归为模型没有发现根因。

## 8. 可复核证据

每个结论均来自以下最新 suite 文件：

```text
/home/host/kverif_runs/kdebug_tool_only_rerun_20260723/results.csv
/home/host/kverif_runs/kdebug_tool_only_rerun_20260723/case_XXX/evidence/with_kdebug/manifest.json
/home/host/kverif_runs/kdebug_tool_only_rerun_20260723/case_XXX/evidence/with_kdebug/*.json
/home/host/kverif_runs/kdebug_tool_only_rerun_20260723/repair/<model>/with_kdebug/case_XXX/trial.log
/home/host/kverif_runs/kdebug_tool_only_rerun_20260723/repair/<model>/with_kdebug/case_XXX/agent_logs/*_transcript.jsonl
/home/host/kverif_runs/kdebug_tool_only_rerun_20260723/repair/<model>/with_kdebug/case_XXX/agent_logs/*_commands.log
/home/host/kverif_runs/kdebug_tool_only_rerun_20260723/repair/_retry_later_archive/<model>/with_kdebug/case_XXX/*
```

最终产物校验见本地 `validation.json`：32 行结果唯一且均为终态，32 张截图非空，3 份
Word 报告共 59 页均完成渲染和页边界检查。

## 9. 不同模型使用 KDebug 证据的汇总结论

第 4 节的内嵌表把“独立采集步骤生成了什么”与“模型实际怎样使用”分开。原始证据来自每个 case 的
KDebug manifest 和 JSON；模型使用情况来自 `evidence_used`、transcript、补丁、build/run/judge
反馈的交叉核对。32 个任务均为 `tool_evidence_valid=true`，但这只说明证据文件通过门禁；
TIMEOUT 行中 `results.csv` 的 `evidence_used` 有些被终态聚合器写成通用描述，因此不能只靠该列
判断模型是否真正理解证据。每个 case 的两模型证据使用链已经分别列在第 4 节对应小节的
“模型证据与无工具对照”表中。

因此，“两个模型拿到相同 manifest”不等于“两个模型从中提取了相同信息”。GPT 对明确文件、
行号和注错常量的利用率更高；Qwen 在 `case_002/005/007` 已有正确诊断，却主要失败在 diff
构造与重复重试，在 `case_009` 则是没有优先处理证据中的直接注错常量。

## 10. 与历史 `without_kdebug` 整体对照

历史基线来自已归档并上传的
`benchmark_results/kdebug_xiangshan_v2_run_20260630_025641_20260704_qwen_final/results.csv`。
“当前”是本报告最新真实 KDebug 工具组，“历史无工具”是旧轮 `without_kdebug`。32 组逐 case、
逐模型结果已放入第 4 节对应 case 的“模型证据与无工具对照”表；下面保留整体终态汇总。

整体终态对照如下：

| 模型 | 最新真实 KDebug 组 | 历史无工具组 | PASS 数变化 |
|---|---:|---:|---:|
| GPT-5.5 | 14 PASS / 2 TIMEOUT | 11 PASS / 5 TIMEOUT | +3 |
| Qwen3.6-35B | 6 PASS / 10 TIMEOUT | 5 PASS / 11 TIMEOUT | +1 |
| 合计 | 20 PASS / 12 TIMEOUT | 16 PASS / 16 TIMEOUT | +4 |

### 10.1 对照限制

1. 这不是同一时间、同一 runner 版本下的随机化 A/B。最新轮只运行了工具组；无工具数据来自
   历史 suite。
2. 两轮之间升级了真实 KDebug manifest 门禁、模型提示、补丁应用、`RETRY_LATER` 归档和
   3600 秒累计预算聚合。API 服务状态和 VM 资源状态也可能不同。
3. 因而 `case_006/007/008` 的 GPT 终态改善及 `case_003/008` 的 Qwen 终态改善，与强 KDebug
   证据的利用链一致，但不能单独证明这些 PASS 全部由 KDebug 导致。
4. Qwen `case_011` 的回退说明跨轮次噪声真实存在：当前轮虽然有 KDebug 佐证，模型仍因环境
   补丁无法落地而 TIMEOUT，历史无工具轮则 PASS。
5. `case_010/016` 的采集 plan 指向错误 RTL，`case_011-016` 又包含环境注错或标签错位，
   不适合作为工具因果效果的核心样本。

下一轮若要量化 KDebug 的净增益，应在同一 runner、同一模型 endpoint、同一 VM 快照和相同
3600 秒预算下同时运行 `with_kdebug` 与 `without_kdebug`，并保持除 evidence 注入外的输入完全一致。
