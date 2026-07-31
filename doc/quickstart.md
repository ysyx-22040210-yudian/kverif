# KVerif 新手 10 分钟上手

这份指南只解决一件事：让第一次接触 KVerif 的验证人员尽快拿到一个真实结果。

这里不讲 NPI procedure，不要求手写 JSON，也不要求先读完整参数手册。所有命令都通过
`tools/kverif` 进入，真实查询仍由安装内的 `kdebug`、`kcov` 和 Verdi 2018 Tcl 后端完成。

## 1. 先记住三个命令

在标准 VM 上以普通用户 `host` 运行：

```bash
su - host
export KVERIF_HOME=/home/host/kverif
export PATH="$KVERIF_HOME/tools:$PATH"
export PYTHON=/usr/local/bin/python3.8

/home/host/kverif/tools/kverif doctor
/home/host/kverif/tools/kverif tutorial waveform
/home/host/kverif/tools/kverif tasks
```

三个命令分别回答：

| 命令 | 回答的问题 | 成功标志 |
| --- | --- | --- |
| `kverif doctor` | 当前用户、Python、KDebug、Verdi、NPI 和 fixture 是否可用 | 最后一行是 `PASS`，required failures 为 0 |
| `kverif tutorial waveform` | 工具能否读取随库的真实 Verdi 2018 FSDB | 变化次数为 5，unknown 为 0，Tutorial checks 为 PASS |
| `kverif tasks` | 当前有哪些面向任务的简单入口 | 列出模块检查、波形检查、教程和脚手架 |

执行教程后会生成：

```text
kverif-results/tutorial/waveform/
  result.json          给人和上层脚本看的简化结论
  tool-response.json   KDebug 返回的原始 JSON 证据
  replay.sh            可原样重放的底层命令
```

先确认这三个文件存在，再开始查询自己的项目。

## 2. 我手里应该准备什么

| 想做的事 | 输入 | 它是什么 |
| --- | --- | --- |
| 看信号值和变化 | `waves.fsdb` | 仿真生成的真实波形文件 |
| 看模块、parameter、端口和连线 | `simv.daidir` | VCS 使用 `-kdb -debug_access+all` 生成的 elaboration database |
| 重新生成教程设计数据库 | RTL + VCS | `tutorial module-inspect` 可以自动完成 |

FSDB 适合回答“这个信号在 95ns 是多少、变化了几次”。`simv.daidir` 适合回答“这个模块
实际例化在哪里、parameter 展开后是多少、端口方向和连接是什么”。两者不是互相替代的文件。

## 3. 第一次分析模块

先运行随库模块教程：

```bash
/home/host/kverif/tools/kverif doctor --require-vcs

/home/host/kverif/tools/kverif tutorial module-inspect \
  --out /home/host/kverif_tutorial
```

如果没有通过 `--daidir`，命令会用随库 RTL 构建一个很小的 VCS 数据库，然后检查
`npi_fixture_top.u_alu`。教程必须得到以下事实才算通过：

```text
WIDTH = 12
BIAS = 1
lhs    input  12 bits
rhs    input  12 bits
result output 12 bits
```

查询自己的模块：

```bash
/home/host/kverif/tools/kverif inspect-module \
  --input /data/project/build/simv.daidir \
  --module tb_top.dut.u_core.u_alu \
  --out /data/project/reports/alu-module
```

`--module` 必须是 elaboration 后的完整实例路径，不是 RTL 中的 module definition 名。
默认查询有效 parameter、端口和直接子实例。需要额外对象时使用：

```bash
/home/host/kverif/tools/kverif inspect-module \
  --input /data/project/build/simv.daidir \
  --module tb_top.dut.u_core.u_alu \
  --sections parameters,ports,io,nets,instances,always_processes \
  --max-rows 500 \
  --out /data/project/reports/alu-module-full
```

只想检查命令，不启动 Verdi：

```bash
/home/host/kverif/tools/kverif inspect-module \
  --input /data/project/build/simv.daidir \
  --module tb_top.dut.u_core.u_alu \
  --dry-run --show-command \
  --out /tmp/alu-query-check
```

## 4. 第一次分析波形

```bash
/home/host/kverif/tools/kverif trace-signal \
  --input /data/project/run/waves.fsdb \
  --signal tb_top.dut.req_valid \
  --begin 0ns \
  --end 2us \
  --format hex \
  --max-rows 500 \
  --out /data/project/reports/req-valid
```

终端直接显示变化次数、X/Z 数量和是否截断。需要全部机器字段时查看
`tool-response.json`，不要从终端文本中用正则猜字段。

## 5. 给脚本使用 JSON

人手运行时不需要 `--json`。Shell、Perl、Python、CI 或内部平台调用时增加 `--json`：

```bash
/home/host/kverif/tools/kverif trace-signal \
  --input /data/project/run/waves.fsdb \
  --signal tb_top.dut.req_valid \
  --begin 0ns --end 2us \
  --out /data/project/reports/req-valid \
  --json > /data/project/reports/req-valid/stdout.json
```

JSON 模式的 stdout 只有一个 JSON object。日志和 Verdi 诊断不会混入协议 stdout。调用脚本还要
检查进程退出码：`0` 表示任务成功，非 `0` 表示输入、环境或底层查询失败。

## 6. 生成一个二次开发起点

不用从长手册里拼第一份脚本。以下命令会生成一个能调用 KDebug、解析 JSON 并形成新结论的
完整目录：

```bash
/home/host/kverif/tools/kverif new signal-check \
  --lang perl \
  --out /data/project/tools/check_req_valid

cd /data/project/tools/check_req_valid
KVERIF_HOME=/home/host/kverif bash ./example.sh
```

`--lang` 支持 `sh`、`csh`、`perl` 和 `python`。生成目录只调用 KVerif 可执行文件，不包含
NPI Tcl、NPI C/C++ 头文件或 KVerif 内部 Python import。

```text
check_req_valid/
  perl/signal_health.pl  业务脚本
  json_response.py       独立 JSON 处理进程，不是 SDK
  example.sh             使用随库真实 FSDB 的可执行例子
  expected.json          预期结论
  README.md              只说明当前任务
```

先跑通 `example.sh`，然后只替换 FSDB、信号、时间窗口和门限。

## 7. 常见错误怎么处理

| 错误码或现象 | 含义 | 下一步 |
| --- | --- | --- |
| `TOOL_NOT_FOUND` | 找不到 `kdebug` | 设置 `KVERIF_HOME`，或传 `--kdebug-bin` |
| `FSDB_NOT_FOUND` | FSDB 路径错误或文件不可见 | 使用绝对路径并检查普通用户权限 |
| `DAIDIR_NOT_FOUND` | 传入的不是实际 `simv.daidir` 目录 | 检查 VCS 构建输出，模块查询不能只传 FSDB |
| `INVALID_MODULE_SECTION` | `--sections` 中有拼错的类别 | 运行 `kverif inspect-module --help` |
| `VCS_NOT_FOUND` | 模块教程无法自动构建设计库 | 设置 `VCS_HOME`，或传已有 `--daidir` |
| `INVALID_TOOL_OUTPUT` | 底层命令没有返回合法 JSON | 运行产物中的 `replay.sh`，查看原始 stderr |
| 教程断言失败 | 工具返回值与随库 manifest/RTL 不一致 | 保留整个输出目录，不要只截最后一行 |

`doctor` 只把完成真实查询所必需的项目记为 required failure。VCS 默认是可选项；只有需要
自动构建模块教程时才使用 `doctor --require-vcs`。

## 8. 接下来读什么

| 现在的目标 | 文档 |
| --- | --- |
| 继续复制任务命令 | 本文和 `kverif <command> --help` |
| 写 Shell/Perl/Python 业务脚本 | [`secondary_development_guide.md`](secondary_development_guide.md) 第 8、9 章 |
| 查某个底层 action 的全部字段 | [`secondary_development_guide.md`](secondary_development_guide.md) 第 10 章 |
| 维护 KDebug/KCov 本身 | 工具目录 README、schema 和 Tcl 引擎文档 |

完整手册是参考资料，不是第一次运行的前置条件。新人应先完成 tutorial，再按任务查表。
