#!/usr/bin/env python3
"""Generate the API-level NPI coverage inventory from the manual outline."""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


MODEL_START = 302
MODEL_END = 1456
LIBRARY_START = 1964
LIBRARY_END = 3232


@dataclass(frozen=True)
class OutlineRow:
    depth: int
    page: int
    title: str


@dataclass(frozen=True)
class ApiEntry:
    family: str
    domain: str
    page: int
    title: str


def read_outline_tsv(path: Path) -> list[OutlineRow]:
    with path.open(newline="", encoding="utf-8") as fp:
        return [
            OutlineRow(int(row["depth"]), int(row["page"]), row["title"].strip())
            for row in csv.DictReader(fp, delimiter="\t")
        ]


def read_pdf_outline(path: Path) -> list[OutlineRow]:
    try:
        from pypdf import PdfReader
        from pypdf.generic import Destination
    except ImportError as exc:
        raise SystemExit("pypdf is required when --pdf is used") from exc

    reader = PdfReader(str(path))
    rows: list[OutlineRow] = []

    def visit(items: Iterable[object], depth: int) -> None:
        last_destination = None
        for item in items:
            if isinstance(item, list):
                visit(item, depth + 1)
                continue
            if isinstance(item, Destination):
                last_destination = item
                rows.append(
                    OutlineRow(
                        depth,
                        reader.get_destination_page_number(item) + 1,
                        str(item.title).strip(),
                    )
                )
                continue
            if last_destination is not None:
                rows.append(
                    OutlineRow(
                        depth,
                        reader.get_destination_page_number(last_destination) + 1,
                        str(item).strip(),
                    )
                )

    visit(reader.outline, 0)
    return rows


def api_entries(rows: Iterable[OutlineRow]) -> list[ApiEntry]:
    entries: list[ApiEntry] = []
    domain = ""
    family = ""
    for row in rows:
        if MODEL_START <= row.page < MODEL_END:
            row_family = "NPI Model"
        elif LIBRARY_START <= row.page < LIBRARY_END:
            row_family = "NPI Library"
        else:
            continue
        if row_family != family:
            family = row_family
            domain = ""
        if row.depth == 1:
            domain = row.title
        elif row.depth == 2 and domain:
            entries.append(ApiEntry(family, domain, row.page, row.title))
    return entries


def normalized_api(title: str) -> str:
    return " ".join(title.replace(" _", "_").split())


def coverage(entry: ApiEntry) -> tuple[str, str, str]:
    name = normalized_api(entry.title)
    lower = name.lower()
    domain = entry.domain

    if domain == "Required Models":
        return "等价覆盖", "KDebug Verdi wrapper", "每次 action 自动初始化、加载目标并关闭 NPI"

    if domain == "Language Model":
        if name == "npi_handle_by_name":
            return "完整覆盖", "language.resolve", "按完整名和可选 scope 解析对象"
        if name in {"npi_iterate", "npi_scan"}:
            return "完整覆盖", "language.iterate", "按受控 npi* object type 遍历"
        if name == "npi_handle":
            return "完整覆盖", "language.relate", "按受控 npi* 一对一关系取对象"
        if name == "npi_get_value":
            return "完整覆盖", "language.value/module.objects", "读取 elaborated 参数或常量值"
        if name in {"npi_get", "npi_get_str"}:
            return "部分覆盖", "language.resolve/module.inspect", "返回固定安全属性集，不接受任意 property 注入"
        if name in {"npi_release_handle", "npi_release_all_handles"}:
            return "内部覆盖", "所有 Tcl action", "action 内释放 handle，handle 不跨进程泄漏"
        if name in {"npi_handle_by_index", "npi_handle_by_range"}:
            return "部分覆盖", "language.resolve", "可解析带 select 的完整名，未单列 handle 索引 action"
        return "未开放", "-", "尚无对应公共 action"

    if domain == "Netlist Model":
        if name in {"npi_nl_cell_handle_by_name", "npi_nl_handle_by_name"}:
            return "完整覆盖", "netlist.resolve", "按名称和可选 npiNl* 类型解析"
        if name in {"npi_nl_iterate", "npi_nl_scan"}:
            return "完整覆盖", "netlist.iterate", "按受控 npiNl* 类型遍历"
        if name in {"npi_nl_get", "npi_nl_get_str"}:
            return "部分覆盖", "netlist.resolve/netlist.iterate", "返回固定网表属性集"
        if name in {"npi_nl_release_handle", "npi_nl_release_all_handles"}:
            return "内部覆盖", "netlist.*", "action 内管理 handle 生命周期"
        return "未开放", "-", "index/range/table 或通用连通关系尚未单列"

    if domain == "Text Model":
        if any(token in lower for token in ("replace_line", "replace_word")):
            return "部分覆盖", "text.replace_line", "仅开放 copy-on-write 行替换"
        if any(token in lower for token in ("file_by_name", "line_by_number", "next_line", "prev_line")):
            return "完整覆盖", "text.line", "文件、行及上下文读取"
        if any(token in lower for token in ("word", "property", "iter_start", "iter_next", "iter_stop")):
            return "完整覆盖", "text.words", "word/TWA 属性和遍历"
        return "未开放", "-", "include/macro 展开或其他文本修改尚未开放"

    if domain == "Design Manipulation (DM) Model":
        if any(token in lower for token in ("module_by_name", "add_net", "clone_module", "write_text_mode")):
            return "部分覆盖", "dm.add_net/dm.clone_module", "仅开放受控 net 添加和 module 克隆写出"
        return "未开放", "-", "通用 DM AST 创建、修改和删除未开放"

    if domain == "FSDB Model":
        return "部分覆盖", "signal.info/scope.list/value.at/value.batch_at/signal.scan", "常用 signal FSDB 查询已覆盖；高级 iterator/member API 未逐项开放"

    if domain == "FSDB Model for Transaction":
        return "未开放", "-", "当前只提供 transaction writer，不提供 transaction FSDB reader"

    if domain == "NPI FSDB Transaction Writer Model":
        return "部分覆盖", "transaction.writer.create", "文件、stream、transaction、tag 和 relation 已覆盖；attribute schema 仍有限"

    if domain == "NPI FSDB Writer Model":
        return "部分覆盖", "fsdb.writer.create_scope", "文件与 scope 层次已覆盖；signal/value change 尚未开放"

    if domain == "NPI Coverage Model":
        if any(token in lower for token in ("set_status", "save_exclusion", "load_exclusion", "unload_exclusion")):
            return "未开放", "-", "KCov 保持只读分析，不修改 exclusion/status"
        return "完整覆盖", "KCov actions", "VDB、test、metric、object、bin 和状态查询由 Tcl NPI 完成"

    if domain == "NPI VCS Model":
        return "部分覆盖", "vcs.summary", "打开真实 VCS DB 并返回固定编译/设计/仿真统计"

    if domain == "NPI Power Model":
        return "许可证阻塞", "power.resolve/power.list", "Tcl action 已实现；当前 VM 缺少 PowerAwareAnalysis license"

    if domain == "NPI CRDB Model":
        return "部分覆盖", "crdb.resolve/crdb.correlates", "对象与 correlation 读取已覆盖；mutation/clone/save-as 未开放"

    if domain == "Module":
        action = "module.find_instances" if "define_" in lower else "module.objects/module.inspect"
        note = "JSON 字段替代 stdout dump；15 类 getter 均有固定 kind 映射"
        return "完整覆盖", action, note

    if domain == "Signal":
        if any(token in lower for token in ("trace", "driver", "load")):
            return "完整覆盖", "trace.driver/trace.load/trace.active_driver", "静态与 active trace 使用 Tcl NPI"
        return "部分覆盖", "signal.resolve/port.trace/interface.resolve", "常用信号与端口映射已覆盖"

    if domain == "Find":
        if "inst" in lower and "def" in lower:
            return "完整覆盖", "module.find_instances", "按 module definition 查全部实例"
        return "未开放", "-", "通用 regex/wildcard find 尚未开放"

    if domain == "VANL Library":
        return "未开放", "-", "无 VANL value propagation session"

    if domain == "Power Library":
        return "许可证阻塞", "power.resolve/power.list", "实现受当前 VM PowerAwareAnalysis license 阻塞"

    if domain == "CRDB Library":
        return "部分覆盖", "crdb.resolve/crdb.correlates", "读取与 correlation 覆盖，写 mapping 未开放"

    if domain == "FSDB Transaction Writer":
        return "部分覆盖", "transaction.writer.create", "常用 writer object/attribute/relation 子集"

    if domain == "FSDB Library":
        return "部分覆盖", "scope.list/signal.info/value.at/signal.scan", "常用 signal FSDB 任务已覆盖"

    if domain == "Connection":
        return "部分覆盖", "port.trace/module.inspect", "Language Model 端口 high/low connection 完整；复杂跨模型 mapping 为部分"

    if domain == "Netlist Library":
        return "部分覆盖", "netlist.resolve/netlist.iterate", "对象查找/遍历已覆盖，all-path/fanin/fanout 尚未开放"

    if domain in {"Hierarchy Tree", "List", "Component"}:
        return "部分覆盖", "module.inspect/scope.list/trace.graph", "公开任务覆盖常用层次读取，不暴露 callback/list handle"

    if domain == "Utilities":
        return "等价覆盖", "KDebug JSON CLI/session", "参数、通信、生命周期由 KDebug 协议层提供"

    if domain == "Miscellaneous":
        return "部分覆盖", "language.resolve/module.inspect", "表达式反编译和常用 HDL 元信息已输出"

    return "未开放", "-", "尚无对应公共 action"


def md_escape(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def write_inventory(entries: list[ApiEntry], output: Path, source: str) -> None:
    by_domain: dict[tuple[str, str], list[ApiEntry]] = defaultdict(list)
    statuses = Counter()
    for entry in entries:
        by_domain[(entry.family, entry.domain)].append(entry)
        statuses[coverage(entry)[0]] += 1

    lines = [
        "# NPI O-2018.09-SP2 API 逐项覆盖清单",
        "",
        "> 本文件由 `kdebug/tools/generate_npi_api_inventory.py` 从手册 outline 生成。",
        f"> 来源：`{source}`。页码为手册页码。",
        "> 重建：`python kdebug/tools/generate_npi_api_inventory.py --pdf <VC_APPS_NPI.pdf> --output doc/npi_api_inventory.md`。",
        "",
        "## 统计口径",
        "",
        f"- API 目录条目：**{len(entries)}** 条。",
        f"- 不同标题：**{len(set(entry.title for entry in entries))}** 个。",
        f"- 功能域：**{len(by_domain)}** 个（13 个 Model 域、15 个 Library 域）。",
        "- 同名 API 在手册中可能因重载或章节重复出现；本表保留每个目录条目以便按页追溯。",
        "- `完整覆盖` 表示公共命令可完成同一用户任务，不表示暴露原始 C/C++ ABI。",
        "- `内部覆盖` 表示 handle 生命周期由一次性 Tcl action 自动管理，不提供无效的跨进程 handle。",
        "",
        "| 判定 | API 条目数 |",
        "| --- | ---: |",
    ]
    status_order = ["完整覆盖", "部分覆盖", "等价覆盖", "内部覆盖", "许可证阻塞", "未开放"]
    for status in status_order:
        lines.append(f"| {status} | {statuses[status]} |")

    lines.extend(
        [
            "",
            "## 功能域汇总",
            "",
            "| 类别 | 功能域 | API 条目 | 完整 | 部分 | 等价/内部 | 许可证阻塞 | 未开放 |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for (family, domain), domain_entries in by_domain.items():
        counts = Counter(coverage(entry)[0] for entry in domain_entries)
        lines.append(
            "| %s | %s | %d | %d | %d | %d | %d | %d |"
            % (
                family,
                md_escape(domain),
                len(domain_entries),
                counts["完整覆盖"],
                counts["部分覆盖"],
                counts["等价覆盖"] + counts["内部覆盖"],
                counts["许可证阻塞"],
                counts["未开放"],
            )
        )

    lines.extend(["", "## 逐 API 清单", ""])
    for (family, domain), domain_entries in by_domain.items():
        lines.extend(
            [
                f"### {family}: {domain}",
                "",
                "| 页码 | API/手册条目 | 判定 | KVerif action | 对照说明 |",
                "| ---: | --- | --- | --- | --- |",
            ]
        )
        for entry in domain_entries:
            status, action, note = coverage(entry)
            lines.append(
                f"| {entry.page} | `{md_escape(normalized_api(entry.title))}` | {status} | "
                f"`{md_escape(action)}` | {md_escape(note)} |"
            )
        lines.append("")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--outline-tsv", type=Path)
    source.add_argument("--pdf", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.outline_tsv:
        rows = read_outline_tsv(args.outline_tsv)
        source_name = "VC_APPS_NPI.pdf 的已提取 outline.tsv"
    else:
        rows = read_pdf_outline(args.pdf)
        source_name = args.pdf.name
    entries = api_entries(rows)
    if len(entries) < 700:
        raise SystemExit(f"manual outline produced only {len(entries)} API entries")
    write_inventory(entries, args.output, source_name)
    print(f"wrote {len(entries)} API entries to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
