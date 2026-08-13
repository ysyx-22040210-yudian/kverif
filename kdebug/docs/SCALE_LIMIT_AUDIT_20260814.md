# kdebug 扩展性限制审计与 XiangShan 压测（2026-08-14）

## 结论

本轮不是只处理 `args.stop_instances` 的 4096 项报错，而是沿请求的完整数据路径审计：

```text
JSON/schema -> C++ frontend -> subprocess/UDS/file transport
            -> Python engine -> argv/environment/plan file -> Verdi Tcl/NPI
```

当前生效的 request schema 中没有固定 `maxItems` 或 `maxLength`。大列表、大字符串、
大响应和超长工作目录不再依赖 argv、单个环境变量、固定缓冲区或默认 64 MiB 文件上限。
资源预算仍然保留，但命中后必须通过 `truncated`、marker 或结构化错误显式暴露，不能
静默制造 `NO_SYSTEM_INSTANCE`、`MODULE_NOT_FOUND` 或部分成功。

## 已消除的同类瓶颈

| 数据通道 | 原风险 | 当前实现与回归 |
| --- | --- | --- |
| `ports` / `stop_instances` | 固定 4096 项校验 | 无固定数量上限；TSV plan 传入 Tcl；真实 50000 stop-set 通过 |
| `target.defines` | 逐项展开到 Verdi argv | 写入私有 `verdi-defines.f`；50000 defines 回归通过 |
| Tcl 标量参数 | 单环境字符串约 128 KiB 时 `execve/E2BIG` | 非路径 `KDEBUG_TCL_*` 统一写入 hex TSV；大于 128 KiB 的 module 全路径经 Python/Tcl 双向验证 |
| `text.replace_line.content` | 正文放入环境变量 | UTF-8 临时文件传输；大于 1 MiB 的正文逐字节验证 |
| file transport JSON | 默认 64 MiB，且类型为 32 位 `int` | 默认不设固定字节上限；正整数 `KDEBUG_FILE_MAX_JSON_BYTES` 才显式限流；65 MiB 请求与响应通过 |
| 当前工作目录 | `getcwd(PATH_MAX)` | 动态扩容；大于 4096 字节的真实 cwd 单元测试通过 |
| 可执行文件路径 | `/proc/self/exe` 固定 4096 字节缓冲 | `readlink` 动态扩容 |
| UDS 响应 | 固定读取块可能被误认为总上限 | 64 KiB 只是循环读取块；大于 1 MiB 响应完整往返 |
| subprocess stdin/stdout | pipe 分块读写 | 2 MiB stdin/stdout 同时传输通过，无死锁或截断 |

每次 NPI 请求还会先清除继承环境中的全部 `KDEBUG_TCL_*`，防止上一次请求的 selector、
payload 或 plan 污染下一次请求。

## 有意保留的边界

- `max_rows`、`max_nodes`、`max_edges` 和各类 depth 是显式资源预算。命中时返回
  `truncated` 或 `TRACE_LIMIT_REACHED:*`，不是传输限制。
- action log 的 4096 字符、64 项数组和 256 KiB 行长，以及 KOUT 的 20 项/4096 字符，
  都只是带 marker 的可读预览；JSON 响应保持完整。
- session name 的 64 字符是稳定标识符契约；长文件系统路径使用 hash 目录名。
- Unix domain socket 的约 104 字节路径来自 `sockaddr_un`，实现会自动切换为 `/tmp` 下的
  稳定 hash 路径。
- `module.inspect.sections` 只有 15 个受支持枚举值；这是能力集合，不是数组传输上限。
- timeout 和显式 `KDEBUG_FILE_MAX_JSON_BYTES` 仍可用于部署侧资源保护。

旧 `src/design`、`src/waveform` direct-engine 代码中的固定缓冲不属于当前 frontend/engine
构建链路；Makefile 的 `audit-tcl-npi-only` 会阻止旧入口重新接入。

## 自动化回归

| 套件 | 结果 |
| --- | --- |
| VM infrastructure | 13 通过 |
| VM schema / examples | 228 / 223 通过 |
| VM action specs | 109 通过 |
| VM contract | 89 通过 |
| VM session | 24 通过 |
| VM C++ unit | 全部通过，包括 65 MiB 可选压力用例 |
| Windows contract | 61 通过、2 条件跳过；其余 Linux ELF 用例在 Windows 不适用 |

65 MiB file transport 压测同时发送 65 MiB request payload 和 65 MiB response payload：
`rc=0`，墙钟 7.58 秒，峰值 RSS 376080 KiB。压测大文件随后删除。

## 真实 XiangShan `elab++` 压测

数据库：

```text
/root/XiangShan-build/build/xverif_xiangshan/kdb/simv.daidir/kdb.elab++
```

最终 50000 stop-set 用例的请求为 2,350,509 字节，真实查找并处理 32 个 MSHR 实例：

- `ok=true`，`processed_instances=32`，`error_count=0`
- 响应 143,966 字节
- 墙钟 52.91 秒，峰值 RSS 1,394,664 KiB
- 响应 SHA-256：
  `9dce1f0711069d6a5b2defea78f2237b9a26a40de8ceded9a7d67ee1fd6828e5`
- `truncated=true` 来自用例显式设置的递归深度预算和对应 marker；stop-set、实例列表和
  响应都没有被数量截断。

其他真实设计证据：

| 用例 | 结果 |
| --- | --- |
| Dispatch `module.inspect` | 响应 15,675,496 字节，5265 ports，`truncated=false`，61.31 秒 |
| `[08]/[09]` 与 `[8]/[9]` | 两份响应逐字节一致，不再触发 Tcl 八进制错误 |
| 32 MSHR + 1 坏 module | 32 成功，坏项独立 `MODULE_NOT_FOUND`，整体 `ok=true` |
| MSHR 常量证据 | 64 条：0 为 48、1 为 16；0 个端口发生 0/1 冲突 |

64 条常量证据全部包含目标端口到常量的 `const_full_path`，source file 均为真实
`/root/XiangShan-build/build/rtl/MSHRCtl.sv`。常量响应为 501,071 字节，SHA-256 为
`846e0eb1846b32017899edfd96a63bbcf143daf235fa49bda71f7642489ca307`。

## 残余风险

取消静态传输上限不代表无限资源。JSON parse 和 Tcl/NPI 结果仍会按输入规模占用内存；
受限部署应显式设置 `KDEBUG_FILE_MAX_JSON_BYTES`、timeout 和 trace 图预算。历史压测已经
证明 4097 个真实复杂 Dispatch 端口的默认完整递归 trace 性能不可接受；该问题需要
persistent Verdi session 和保持 stop cut-set 语义的事务性分块，不能重新引入固定数量
限制来掩盖。
