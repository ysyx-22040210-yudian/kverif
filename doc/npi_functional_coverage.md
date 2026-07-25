# KVerif 对 NPI O-2018.09-SP2 的功能覆盖审计

## 1. 结论

当前 KVerif **不能覆盖 NPI 手册的全部功能**。

此前按 `npi_*` 符号数量得到的约 6.6% 只能表示“生产 Tcl 中直接出现过多少个 API 名称”，
不能作为功能覆盖率，原因是手册大量存在以下重复形态：

- C/C++ API 与 Tcl command 是同一能力的不同绑定；
- `by_name`、`by_hdl`、`by_index`、`by_range` 是同一查找能力的不同入口；
- `get`、`get_str`、`get_value` 是属性读取的类型变体；
- `iter_start`、`iter_next`、`iter_stop` 共同组成一次遍历能力；
- `dump` 与返回 handle/vector 的版本只改变输出方式；
- NPI Library 的许多函数是基于 NPI Model 实现的便利封装；
- scalar/vector、signal/handle 等重载并不代表新的用户任务。

本审计按“用户能否完成一个独立任务”归并为 70 个规范化能力单元。结果为：

| 判定 | 数量 | 含义 |
| --- | ---: | --- |
| 完整覆盖 | 23 | 公共 KVerif 命令可以完成该任务；不要求逐个暴露底层重载 |
| 部分覆盖 | 22 | 只能完成该任务的一个重要子集，或缺少通用对象/属性/方向 |
| 等价或间接覆盖 | 2 | KVerif 自己完成生命周期或传输，但不暴露对应 NPI 对象语义 |
| 未覆盖 | 23 | 当前公共工具和生产 Tcl 均没有等价能力 |

这里不再给出单一百分比。70 个能力单元没有相同业务权重；例如“读取一个 FSDB 值”和
“构造并重写完整 HDL 设计”不能按 1:1 的产品价值加权。

## 2. 审计边界

- 手册：`VC_APPS_NPI.pdf`，3568 页，标题页为 **Version O-2018.09-SP2, March 2019**。
- 该版本与 VM 的 Verdi `Verdi_O-2018.09-SP2` 一致。
- 生产直接 NPI 入口仅审计：
  - `kdebug/tcl_engine/kdebug_npi.tcl`
  - `kcov/tcl_engine/kcov_npi.tcl`
- KDebug 的 Python 层可以组合多个 Tcl 查询形成更高层分析，但组合 action 不重复计为新的
  NPI 原子能力。
- KCov 的过滤、汇总、导出和 session 管理由 Python 完成；VDB 事实读取仍由 Tcl NPI 完成。
- 测试、示例、历史报告和 `tmp` 中出现的 API 名称不算生产覆盖。

## 3. 归并规则

1. 相同输入对象和相同结果语义的 API 合并，不按函数名计数。
2. 只改变输入载体的重载合并，例如 name/handle/vector。
3. 只改变输出载体的重载合并，例如 return/dump。
4. iterator 的创建、前进和释放合并为一个“遍历”任务。
5. Model API 与基于它实现的 L1 Library API 如能完成同一任务，只计一次。
6. 读、写、修改分别计数，因为它们对用户工作流和风险完全不同。
7. RTL language model、flattened netlist、FSDB waveform、transaction FSDB、VDB、CRDB
   不互相替代；即使都存在 `handle/get/iterate`，其数据域不同。
8. “部分覆盖”必须有可调用的公共入口；仅存在内部 helper 不算覆盖。

## 4. 规范化能力矩阵

### A. Runtime 与 Language Model（手册 12-61 页）

| ID | 规范化能力 | 合并的典型 API 形态 | 判定 | 当前依据或缺口 |
| --- | --- | --- | --- | --- |
| A1 | 初始化、加载和关闭设计 | `npi_init/load_design/end` | 等价/间接 | wrapper 启动 Verdi 并加载 daidir，但用户不能操作通用 NPI design session |
| A2 | 按完整名称解析 HDL 对象 | `npi_handle_by_name` | 完整 | `signal.resolve`、`signal.canonicalize` |
| A3 | 任意 HDL 对象关系遍历 | `npi_handle/iterate/scan` | 部分 | 只对 driver/load、少量端口和控制关系提供专用 action |
| A4 | 任意 HDL 对象属性读取 | `npi_get/get_str` | 部分 | 固定读取 name/full-name/type/file/line，不能请求任意 property |
| A5 | Language Model 对象值读取 | `npi_get_value` | 未覆盖 | 波形值来自 FSDB，不等价于通用 Language Model value |
| A6 | handle 比较、重叠、range、永久化和批量释放 | compare/overlap/range/permanent/release-all | 未覆盖 | 仅内部逐个释放 handle |

### B. Netlist Model（手册 62-87 页）

| ID | 规范化能力 | 合并的典型 API 形态 | 判定 | 当前依据或缺口 |
| --- | --- | --- | --- | --- |
| B1 | flattened netlist 对象查找 | `npi_nl_*_by_name/index/range/table_lookup` | 完整 | `netlist.resolve` 支持名称和 `npiNl*` 类型约束 |
| B2 | netlist 层次和对象遍历 | `npi_nl_handle/iterate/scan` | 部分 | `netlist.iterate` 可按 reference 和对象类型遍历，但未暴露全部 method 方向 |
| B3 | netlist 属性读取 | `npi_nl_get/get_str` | 部分 | 返回 name/full-name/type/size 等固定字段，不允许任意 property |
| B4 | net/instance/port/inst-port 连通关系 | netlist connection methods | 未覆盖 | 不支持技术无关 flattened netlist connectivity |

### C. Text Model（手册 88-95 页）

| ID | 规范化能力 | 合并的典型 API 形态 | 判定 | 当前依据或缺口 |
| --- | --- | --- | --- | --- |
| C1 | 源文件和行上下文读取 | file/line lookup、next/prev line | 完整 | `text.line` 使用 Text Model 定位文件和行；`source.context` 提供扩展上下文 |
| C2 | word 对象和 TWA 属性读取 | text word/property/property-str | 完整 | `text.words` 返回 word、序号和 Text Word Attribute |
| C3 | include/macro 解析与展开 | `expand_include/expand_macro` | 未覆盖 | 无等价 action |
| C4 | 文本插入、删除和替换 | insert/delete/replace line/word | 部分 | `text.replace_line` 支持 copy-on-write 行替换；插入、删除和 word 编辑仍未覆盖 |

### D. Design Manipulation Model（手册 96-135 页）

| ID | 规范化能力 | 合并的典型 API 形态 | 判定 | 当前依据或缺口 |
| --- | --- | --- | --- | --- |
| D1 | DM database/session 创建、加载、保存和删除 | create-db、load/save/delete-session | 未覆盖 | 无 `npi_dm_*` 生产调用 |
| D2 | DM 对象查找、遍历、属性和值读取 | handle/iter/property/get-value/decompile | 部分 | `dm.add_net/clone_module` 可按名解析 module definition；通用遍历、属性和值读取未开放 |
| D3 | module/interface/package/type/signal/port 创建 | create/add design objects and types | 部分 | `dm.add_net` 可创建 wire/bus net；其他对象类型仍未开放 |
| D4 | 表达式、语句、过程和控制结构构造 | create operation/statement/process/control | 未覆盖 | 不构造 DM AST |
| D5 | 层次、实例、参数、端口和连接修改 | connect/move/modify hierarchy/assign parameter | 未覆盖 | 无设计重构入口 |
| D6 | 删除、重命名、替换、格式同步和写出 | delete/rename/replace/sync/write | 部分 | `dm.clone_module` 和 `dm.add_net` 可写出新设计目录；通用删除/重命名/同步未覆盖 |

### E. FSDB Signal Waveform Model（手册 136-161 页）

| ID | 规范化能力 | 合并的典型 API 形态 | 判定 | 当前依据或缺口 |
| --- | --- | --- | --- | --- |
| E1 | FSDB 打开、关闭、时间范围、时间单位和文件属性 | open/close/min/max/file-property/time-convert | 完整 | KDebug Tcl 后端直接实现 |
| E2 | scope/signal 精确查找 | scope/sig-by-name | 完整 | `scope.list`、`signal.info`、`value.at` |
| E3 | scope 和 signal 层次枚举 | top/child scope、top/scope signal iterators | 部分 | 支持常用枚举；未覆盖 parent/member 和全部关系方向 |
| E4 | scope/signal 元数据读取 | property/property-str/file/parent/scope | 部分 | 暴露名称、类型、位宽等固定字段，不是全部属性 |
| E5 | 单信号指定时间取值 | value-at、VCT value | 完整 | `value.at`，支持 bin/dec/hex |
| E6 | 多信号同一时间批量取值 | scalar/vector value-at variants | 完整 | `value.batch_at` |
| E7 | 单信号时间窗口内 value-change 遍历 | create/release VCT、goto、next、time/value | 完整 | `signal.scan`、`signal.changes` |
| E8 | 向前/向后查值、查 X 和事件定位 | find-value/find-x forward/backward | 部分 | 可用 scan 和 `event.find` 组合，缺少高效反向原语 |
| E9 | time-based iterator、signal-list 批量装载和 update/unload | FT、add/reset list、load/unload/update | 未覆盖 | 当前只做单信号 VCT 和同一时刻 batch |
| E10 | member/relation/port value、duration、sequence 等专用数据 | member、port-value、duration、seq-num | 未覆盖 | 无对应输出字段和 action |

### F. FSDB Waveform Data Mining（手册 162-179 页）

| ID | 规范化能力 | 判定 | 当前依据或缺口 |
| --- | --- | --- | --- |
| F1 | 握手、脉冲、稳定性和窗口模式检测 | 完整 | `handshake.inspect`、`sampled_pulse.inspect`、`window.verify`、`verify.conditions` |
| F2 | 统计、趋势、事件及 APB/AXI/stream 协议分析 | 完整 | KDebug 基于真实 FSDB value-change 组合分析，能力超过手册示例 |

### G. Transaction FSDB Reader（手册 180-203 页）

| ID | 规范化能力 | 合并的典型 API 形态 | 判定 |
| --- | --- | --- | --- |
| G1 | transaction scope/stream 查找和遍历 | stream/scope lookup and iterators | 未覆盖 |
| G2 | 按时间或 transaction ID 定位和遍历 transaction | create-trt/by-id/goto/iter | 未覆盖 |
| G3 | scope/stream/transaction attribute 和 expected attribute 读取 | attr/count/value/expected | 未覆盖 |
| G4 | transaction relation 和 related transaction 遍历 | relation iterators/properties | 未覆盖 |
| G5 | stream-list 和 transaction range 装载/卸载 | add/reset stream list、load/unload trans | 未覆盖 |

### H. Transaction FSDB Writer（手册 204-223 页）

| ID | 规范化能力 | 判定 |
| --- | --- | --- |
| H1 | writer 文件生命周期、flush 和时间推进 | 完整 |
| H2 | stream 定义、属性定义和 stream attribute | 部分：可定义 stream，尚不支持 stream attribute schema |
| H3 | transaction begin/end、label、tag、value/expected attribute | 部分：支持 begin/end、label、tag，尚不支持 value/expected attribute |
| H4 | transaction relation 写入 | 完整 |

### I. FSDB Signal Writer（手册 224-231 页）

| ID | 规范化能力 | 判定 |
| --- | --- | --- |
| I1 | 创建、flush 和关闭 FSDB | 完整 |
| I2 | 创建 scope、signal、array/memory 等层次对象 | 部分：`fsdb.writer.create_scope` 可创建嵌套 scope，signal/array/memory 尚未开放 |
| I3 | 推进时间、写 value change 和控制 dump | 未覆盖 |

### J. Coverage Model（手册 262-275 页）

| ID | 规范化能力 | 合并的典型 API 形态 | 判定 | 当前依据或缺口 |
| --- | --- | --- | --- | --- |
| J1 | VDB 打开和关闭 | `npi_cov_open/close` | 完整 | KCov Tcl 后端直接实现 |
| J2 | test 枚举、按名选择 | test iterator/test-by-name | 完整 | `tests.list` 和具体 test 查询 |
| J3 | 多 test 合并 | `npi_cov_merge_test` | 完整 | 默认 `merged` 查询 |
| J4 | scope、metric、object、bin 层次遍历和属性读取 | handle/iter/get/get-str | 完整 | code、assert、functional、power metric 均可走 items |
| J5 | covered/uncovered/excluded/proven 等状态读取 | `get/has_status` | 完整 | `cov.holes`、summary 和 status 数组 |
| J6 | test 保存和显式 unload | save/unload-test | 未覆盖 | 当前只在进程生命周期内合并和关闭数据库 |
| J7 | exclusion file、status 修改和 exclusion unload | load/save exclusion、set/set-status | 未覆盖 | KCov 是只读分析工具 |

### K. VCS Model（手册 276-285 页）

| ID | 规范化能力 | 判定 | 当前缺口 |
| --- | --- | --- | --- |
| K1 | 打开和关闭带 `-Xdump_vcsdb` 的 VCS database | 完整 | `vcs.summary` 通过 Tcl NPI 打开、汇总并关闭数据库 |
| K2 | 编译/仿真 warning、error、CPU time 和设计统计查询 | 部分 | `vcs.summary` 返回 warning/error/module 等固定统计；并非全部 VCS property |

### L. Power Model（手册 240-261 页）

| ID | 规范化能力 | 判定 |
| --- | --- | --- |
| L1 | power object/domain 查找、遍历和属性读取 | 部分：`power.resolve/list` 已实现 daidir 与 RTL+UPF 源码加载；VM 缺少 `PowerAwareAnalysis` license，业务结果未完成实测 |
| L2 | power-domain crossing 检测和路径分析 | 未覆盖 |
| L3 | instance、power domain、primary power/ground 映射 | 未覆盖 |
| L4 | supply driver/load 和 supply network path | 未覆盖 |

### M. CRDB Model（手册 232-239 页）

| ID | 规范化能力 | 判定 |
| --- | --- | --- |
| M1 | CRDB 打开、关闭、clone/save-as 和 handle 生命周期 | 部分：action 内部安全打开/关闭和释放 handle；未开放 clone/save-as |
| M2 | CRDB 对象查找、遍历和属性读取 | 部分：`crdb.resolve` 支持 RTL/GATE 名称查找和固定属性；通用层次遍历未开放 |
| M3 | correlation 设置、取消、检查和 mapping | 部分：`crdb.correlates` 可读取 mapping；set/unset mutation 未开放 |

### N. Leading Trace 与 NPI Libraries（手册 286-301、1900-3231 页）

此处把建立在前述 Model 上、仅改变 name/handle/vector/dump 形式的 L1 API 合并回同一任务，
不把数百个便利函数重复计数。

| ID | 规范化能力 | 合并的典型 Library 形态 | 判定 | 当前依据或缺口 |
| --- | --- | --- | --- | --- |
| N1 | RTL source-level 静态 driver/load trace | trace-driver/load name/hdl/dump variants | 完整 | `trace.driver`、`trace.load`、`trace.graph/path/expand` |
| N2 | 指定时刻 active driver trace | active-trace name/hdl/dump variants | 完整 | `trace.active_driver` |
| N3 | 多跳 active-driver chain | repeated active trace | 完整 | `trace.active_driver_chain` |
| N4 | flattened-netlist fan-in/fan-out register 和 all-path trace | `npi_nl_*trace*`、report-all-path | 未覆盖 | 当前 trace 是 RTL/Language Model 路径 |
| N5 | module port 高低连接、跨层映射和 equivalent signal | connection/equivalent-signal variants | 部分 | `port.trace`、`instance.map`、`interface.resolve` 覆盖常用场景，不是通用 netlist mapping |
| N6 | VANL value set/propagate/get 和路径分析 | `npi_vanl_*` | 未覆盖 | 无 VANL session |
| N7 | instance/signal regex 与 wildcard 查找 | `npi_find_*` | 未覆盖 | 只支持精确 resolve；`signal.search` 已移除 |
| N8 | 通用 hierarchy/module/component/list 遍历 | hier-tree、module/component/list libraries | 部分 | 有 scope/source/instance 专用 action，无通用 handle 列表和 callback |
| N9 | expression decompile、expression traverse、typespec 工具 | expr/typespec/hdl-info utilities | 部分 | expression decompile 已用；callback traversal 和完整 typespec 工具缺失 |
| N10 | 参数解析、命令通信、session 和层次名工具 | arg/socket/communicate/usn | 等价/间接 | KVerif 以 JSON CLI、stdio-loop、MCP 和 session manager 提供等价工作流，不暴露 NPI utility object |

## 5. Verdi 2018 VM 实测

2026-07-24 在 VM `192.168.31.116` 上由普通用户 `host` 使用
`Verdi_O-2018.09-SP2` 执行 `kdebug/tests/vm/npi_actions/run.sh`。测试从源码构建最小
VCS/KDB 和 CRDB，调用公共 `tools/kdebug` 命令，不直接运行内部 Tcl procedure。

| 结果 | action | 证据摘要 |
| --- | --- | --- |
| PASS | `npi.capabilities` | 11/11 NPI 域的目标 Tcl command 可用 |
| PASS | `netlist.resolve/iterate` | 解析 `result[7:0]`，遍历 4 个 net |
| PASS | `text.line/words/replace_line` | 读取 12 个 word，并生成非空 patched source |
| PASS | `dm.add_net/clone_module` | 两个 DM writer 输出目录均含非空文件 |
| PASS | `vcs.summary` | 真实 `-Xdump_vcsdb` 数据库返回 2 个 module、0 error |
| PASS | `transaction.writer.create` | 生成非空 FSDB，含 2 个 transaction 和 1 个 relation |
| PASS | `fsdb.writer.create_scope` | 生成非空 FSDB，含 3 个 scope；重复输出返回 `OUTPUT_EXISTS` |
| PASS | `crdb.resolve/correlates` | CRDB 构建成功，RTL `state` 返回 1 个真实 gate correlation |
| LICENSE BLOCKED | `power.resolve/list` | RTL+UPF 已由 Verdi 源码模式加载；VM 不提供 `PowerAwareAnalysis` feature |

机器可读结果见
[`vm-summary.json`](../kdebug/tests/vm/npi_actions/evidence/vm-summary.json)，每个 action 的原始
response 见同目录 `responses/`。Power 两项是已执行后的环境阻塞，不计为 PASS，也不计为
Tcl 实现失败。

## 6. 当前真实强项

1. **FSDB 信号波形读取与派生分析**：时间点值、批量值、value-change、事件、统计、握手、
   APB/AXI/stream 分析是当前最完整的能力域。
2. **RTL 调试 trace**：精确信号解析、driver/load、active driver 和多跳链已形成面向用户的稳定流程。
3. **Coverage 只读分析**：VDB test、scope、metric、bin、状态、holes、summary 和导出覆盖较完整。
4. **受控 NPI 专用任务**：Netlist、Text、有限 DM 修改、VCS summary、两类 writer 和 CRDB
   mapping 已有独立 schema、公共 CLI 和 Verdi 2018 实测。

## 7. 最大缺口

1. **写/改路径仍是窄子集**：只有行替换、add-net、clone-module、transaction writer 和 scope-only
   FSDB writer；通用 AST/层次重构、signal value writer 和 coverage exclusion mutation 仍缺失。
2. **专用模型仍不完整**：transaction FSDB reader、Power crossing/network、完整 Netlist connectivity、
   VCS 任意 property 和 CRDB mutation 尚未覆盖。
3. **通用对象模型不足**：当前以任务型 action 为主，不允许调用者任意选择 object type、method、property。
4. **高级 library 子域不足**：VANL、regex/wildcard find、netlist fan-in/fan-out、通用 hierarchy callbacks。

## 8. 产品口径建议

- 不应宣称“KVerif 覆盖全部 NPI”或给出基于符号数的覆盖率。
- 可准确描述为：
  **KVerif 覆盖 Verdi O-2018.09-SP2 NPI 中面向 RTL trace、FSDB waveform、VDB coverage
  的核心工作流，并提供 Netlist、Text/有限 DM 修改、transaction/scope writer、VCS 和 CRDB
  的任务型子集；它不等价于 NPI 的完整通用对象模型。Power 查询已实现，但仍需具备
  `PowerAwareAnalysis` license 的环境完成业务数据实测。**
- 后续扩展应按本矩阵增加独立 Tcl action 和 VM 实测，不应为了提高 API 名称数量机械包装重载。
