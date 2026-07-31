#!/usr/bin/env python3
"""Build and validate the commercial KVerif secondary-development PDF manual."""

from __future__ import annotations

import ast
import csv
import hashlib
import html
import json
import os
import re
import subprocess
import sys
import textwrap
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any, Iterable

from reportlab.graphics.shapes import Drawing, Line, Rect, String
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    CondPageBreak,
    Frame,
    HRFlowable,
    KeepTogether,
    LongTable,
    NextPageTemplate,
    PageBreak,
    PageBreakIfNotEmpty,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

from kverif_manual_catalog import (
    ACTION_PURPOSE,
    ENVIRONMENT_ROWS,
    FIELD_DESCRIPTIONS,
    KBERIF_COMMANDS,
    KBIT_COMMANDS,
    KBIT_PARAM_ROWS,
    KCOV_COMMANDS,
    KCOV_COMMON_OPTIONS,
    KDEBUG_CLI_OPTIONS,
    KDEBUG_SHORTCUTS,
    KEDA_COMMANDS,
    KENTRY_COMMANDS,
    KLOC_COMMANDS,
    KSVA_COMMANDS,
    LIMIT_DESCRIPTIONS,
    LOOP_CLIENT_COMMANDS,
    OUTPUT_DESCRIPTIONS,
    TARGET_DESCRIPTIONS,
    TOOL_MATRIX,
)


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "output" / "pdf"
TMP_DIR = ROOT / "tmp" / "pdfs" / "kverif_secondary_manual"
OUT_PDF = OUT_DIR / "KVerif_Secondary_Development_Manual.pdf"
AUDIT_JSON = OUT_DIR / "KVerif_Secondary_Development_Manual.audit.json"
VERSION = "1.1"
PUBLICATION_DATE = "2026-08-01"
KDEBUG_BIN = "/home/host/kverif/tools/kdebug"
KCOV_BIN = "/home/host/kverif/tools/kcov"

NPI_WORKFLOW_ACTIONS = {
    "npi.capabilities",
    "language.resolve", "language.iterate", "language.relate", "language.value",
    "module.find_instances", "module.inspect", "module.objects",
    "netlist.resolve", "netlist.iterate",
    "text.line", "text.words", "text.replace_line",
    "dm.add_net", "dm.clone_module",
    "vcs.summary", "power.resolve", "power.list",
    "crdb.resolve", "crdb.correlates",
    "transaction.writer.create", "fsdb.writer.create_scope",
}

MODULE_OBJECT_KINDS = {
    "continuous_assignments", "functions", "generate_scopes", "instances",
    "instances_in_generate", "io", "language_interfaces", "nets", "parameters",
    "ports", "primitives", "always_processes", "initial_processes", "tasks", "variables",
}

WORKFLOW_COVERAGE = [
    {
        "task": "定义到实例与实际参数",
        "title": "演示：查找模块实例和实际参数值",
        "actions": ["module.find_instances", "module.inspect", "module.objects", "language.value"],
        "kinds": ["parameters"],
        "evidence": "Verdi 2018 VM 10/10 PASS",
    },
    {
        "task": "端口、方向、位宽与上下层连线",
        "title": "演示：模块端口、方向、位宽与上下层连线",
        "actions": ["module.inspect", "module.objects", "language.relate"],
        "kinds": ["ports", "io"],
        "evidence": "ports/io/relate 各 10/10 PASS",
    },
    {
        "task": "普通实例、generate 实例和 primitive 层次",
        "title": "演示：列出普通实例、generate 实例和 primitive",
        "actions": ["module.objects", "module.find_instances"],
        "kinds": ["instances", "generate_scopes", "instances_in_generate", "primitives"],
        "evidence": "4 kind 各 10/10 PASS",
    },
    {
        "task": "内部对象、过程与源码位置",
        "title": "演示：模块内部对象、过程与源码位置",
        "actions": ["module.objects", "text.line"],
        "kinds": ["nets", "variables", "functions", "tasks", "continuous_assignments",
                  "always_processes", "initial_processes", "language_interfaces"],
        "evidence": "8 kind 与 text.line 各 10/10 PASS",
    },
    {
        "task": "对照 RTL 对象和展开后的网表对象",
        "title": "演示：对照 RTL 设计对象和展开后的网表对象",
        "actions": ["language.resolve", "language.iterate", "language.relate",
                    "netlist.resolve", "netlist.iterate"],
        "kinds": [],
        "evidence": "5 项操作各 10/10 PASS",
    },
    {
        "task": "读取源码并在副本中修改设计",
        "title": "演示：读取源码并在副本中修改设计",
        "actions": ["text.line", "text.words", "text.replace_line", "dm.add_net", "dm.clone_module"],
        "kinds": [],
        "evidence": "5 项操作各 10/10 PASS",
    },
    {
        "task": "运行环境与跨层数据库",
        "title": "演示：NPI 能力、VCS 与 CRDB 跨层检查",
        "actions": ["npi.capabilities", "vcs.summary", "crdb.resolve", "crdb.correlates"],
        "kinds": [],
        "evidence": "4 项操作各 10/10 PASS",
    },
    {
        "task": "创建 FSDB 并检查 Power 许可证",
        "title": "演示：创建 Transaction/FSDB 并检查 Power 许可证",
        "actions": ["transaction.writer.create", "fsdb.writer.create_scope", "power.resolve", "power.list"],
        "kinds": [],
        "evidence": "两项 FSDB 创建操作共 20/20 PASS；Power 共 20 次许可阻塞",
    },
]

PAGE_W, PAGE_H = A4
LEFT = 17 * mm
RIGHT = 15 * mm
TOP = 18 * mm
BOTTOM = 16 * mm
CONTENT_W = PAGE_W - LEFT - RIGHT

INK = HexColor("#172127")
MUTED = HexColor("#5F6B72")
PAPER = HexColor("#F7F8F6")
WHITE = colors.white
TEAL = HexColor("#006D77")
TEAL_DARK = HexColor("#004C52")
TEAL_LIGHT = HexColor("#E4F1F1")
AMBER = HexColor("#E19A2A")
AMBER_LIGHT = HexColor("#FFF3D8")
RED = HexColor("#B63A3A")
RED_LIGHT = HexColor("#FBEAEA")
BLUE = HexColor("#286A9E")
BLUE_LIGHT = HexColor("#E8F1F8")
GRID = HexColor("#D7DEE0")
CODE_BG = HexColor("#152126")
CODE_FG = HexColor("#E9F3F1")


def register_fonts() -> tuple[str, str, str, str]:
    candidates = {
        "body": ("KVerifSans", Path(r"C:\Windows\Fonts\msyh.ttc"), 0),
        "bold": ("KVerifSansBold", Path(r"C:\Windows\Fonts\msyhbd.ttc"), 0),
        "light": ("KVerifSansLight", Path(r"C:\Windows\Fonts\msyhl.ttc"), 0),
        "mono": ("KVerifMono", Path(r"C:\Windows\Fonts\consola.ttf"), 0),
    }
    loaded: dict[str, str] = {}
    for key, (name, path, index) in candidates.items():
        try:
            pdfmetrics.registerFont(TTFont(name, str(path), subfontIndex=index))
            loaded[key] = name
        except Exception:
            loaded[key] = "Helvetica-Bold" if key == "bold" else "Helvetica"
    return loaded["body"], loaded["bold"], loaded["light"], loaded["mono"]


FONT, FONT_BOLD, FONT_LIGHT, FONT_MONO = register_fonts()


def make_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    styles: dict[str, ParagraphStyle] = {}
    styles["Body"] = ParagraphStyle(
        "Body", parent=base["BodyText"], fontName=FONT, fontSize=9.1,
        leading=14.2, textColor=INK, spaceAfter=5.5, wordWrap="CJK",
    )
    styles["BodySmall"] = ParagraphStyle(
        "BodySmall", parent=styles["Body"], fontSize=7.7, leading=11.2,
        textColor=MUTED, spaceAfter=3,
    )
    styles["H1"] = ParagraphStyle(
        "H1", parent=base["Heading1"], fontName=FONT_BOLD, fontSize=21,
        leading=27, textColor=TEAL_DARK, spaceBefore=4, spaceAfter=11,
        keepWithNext=True,
    )
    styles["H2"] = ParagraphStyle(
        "H2", parent=base["Heading2"], fontName=FONT_BOLD, fontSize=14.5,
        leading=20, textColor=INK, spaceBefore=12, spaceAfter=7,
        keepWithNext=True,
    )
    styles["H3"] = ParagraphStyle(
        "H3", parent=base["Heading3"], fontName=FONT_BOLD, fontSize=11.2,
        leading=15.5, textColor=TEAL_DARK, spaceBefore=9, spaceAfter=5,
        keepWithNext=True,
    )
    styles["H4"] = ParagraphStyle(
        "H4", parent=styles["Body"], fontName=FONT_BOLD, fontSize=9.5,
        leading=13, textColor=INK, spaceBefore=6, spaceAfter=3,
        keepWithNext=True,
    )
    styles["CoverTitle"] = ParagraphStyle(
        "CoverTitle", fontName=FONT_BOLD, fontSize=31, leading=38,
        textColor=WHITE, spaceAfter=10,
    )
    styles["CoverSub"] = ParagraphStyle(
        "CoverSub", fontName=FONT_LIGHT, fontSize=15, leading=21,
        textColor=HexColor("#CDE3E2"), spaceAfter=8,
    )
    styles["CoverMeta"] = ParagraphStyle(
        "CoverMeta", fontName=FONT, fontSize=9.2, leading=14,
        textColor=HexColor("#D8E5E4"),
    )
    styles["TableHead"] = ParagraphStyle(
        "TableHead", fontName=FONT_BOLD, fontSize=7.5, leading=10,
        textColor=WHITE, wordWrap="CJK",
    )
    styles["TableCell"] = ParagraphStyle(
        "TableCell", fontName=FONT, fontSize=7.35, leading=10.2,
        textColor=INK, wordWrap="CJK",
    )
    styles["TableCellSmall"] = ParagraphStyle(
        "TableCellSmall", parent=styles["TableCell"], fontSize=6.45, leading=8.7,
    )
    styles["Code"] = ParagraphStyle(
        "Code", fontName=FONT_MONO, fontSize=6.7, leading=9.2,
        textColor=CODE_FG, leftIndent=0, rightIndent=0, wordWrap="CJK",
    )
    styles["CodeCJK"] = ParagraphStyle(
        "CodeCJK", fontName=FONT, fontSize=6.8, leading=9.4,
        textColor=CODE_FG, leftIndent=0, rightIndent=0, wordWrap="CJK",
    )
    styles["InlineCode"] = ParagraphStyle(
        "InlineCode", parent=styles["Body"], fontName=FONT_MONO, fontSize=8,
    )
    styles["Callout"] = ParagraphStyle(
        "Callout", parent=styles["Body"], fontSize=8.5, leading=12.8,
        spaceAfter=0,
    )
    styles["Bullet"] = ParagraphStyle(
        "Bullet", parent=styles["Body"], leftIndent=12, firstLineIndent=-7,
        bulletIndent=0, spaceAfter=3,
    )
    styles["TOC0"] = ParagraphStyle(
        "TOC0", fontName=FONT_BOLD, fontSize=9.8, leading=13.5,
        leftIndent=0, firstLineIndent=0, textColor=TEAL_DARK, spaceBefore=2,
    )
    styles["TOC1"] = ParagraphStyle(
        "TOC1", fontName=FONT, fontSize=8.1, leading=11.2,
        leftIndent=16, firstLineIndent=0, textColor=INK,
    )
    return styles


STYLES = make_styles()


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def mono(value: Any) -> str:
    return f'<font name="{FONT_MONO}">{esc(value)}</font>'


def slug(value: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip()).strip("-").lower()
    return clean or hashlib.sha1(value.encode("utf-8")).hexdigest()[:10]


def p(text: str, style: str = "Body") -> Paragraph:
    return Paragraph(text, STYLES[style])


def heading(text: str, level: int, anchor: str | None = None,
            toc: bool = True, outline: bool = True) -> Paragraph:
    anchor = anchor or f"h-{slug(text)}"
    flow = Paragraph(f'<a name="{esc(anchor)}"/>{text}', STYLES[f"H{level}"])
    flow._bookmark_name = anchor  # type: ignore[attr-defined]
    flow._heading_text = re.sub(r"<[^>]+>", "", text)  # type: ignore[attr-defined]
    flow._outline_level = min(level - 1, 2) if outline else None  # type: ignore[attr-defined]
    flow._toc_level = level - 1 if toc and level <= 2 else None  # type: ignore[attr-defined]
    return flow


def soft_code_line(line: str) -> str:
    leading = len(line) - len(line.lstrip(" "))
    raw = esc(line[leading:])
    return "&#160;" * leading + raw


def code_block(text: str, label: str | None = None, max_lines: int = 34) -> list[Any]:
    text = text.strip("\n")
    lines = text.splitlines()
    if len(lines) > max_lines:
        keep_head = max(6, max_lines - 5)
        lines = lines[:keep_head] + [f"... output excerpt: {len(text.splitlines()) - keep_head} lines omitted ..."]
    markup = "<br/>".join(soft_code_line(line) if line else "&#160;" for line in lines)
    code_style = STYLES["CodeCJK"] if any(ord(char) > 127 for char in text) else STYLES["Code"]
    cell = Paragraph(markup, code_style)
    box = Table([[cell]], colWidths=[CONTENT_W], hAlign="LEFT")
    box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CODE_BG),
        ("BOX", (0, 0), (-1, -1), 0.5, HexColor("#294148")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    result: list[Any] = []
    if label:
        result.append(p(f"<b>{esc(label)}</b>", "BodySmall"))
        return [KeepTogether([*result, box]), Spacer(1, 5)]
    return [box, Spacer(1, 5)]


def callout(title: str, body: str, tone: str = "info") -> Table:
    palette = {
        "info": (BLUE_LIGHT, BLUE),
        "note": (TEAL_LIGHT, TEAL),
        "warn": (AMBER_LIGHT, AMBER),
        "danger": (RED_LIGHT, RED),
    }
    bg, edge = palette[tone]
    content = Paragraph(f"<b>{esc(title)}</b><br/>{body}", STYLES["Callout"])
    table = Table([[content]], colWidths=[CONTENT_W])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("LINEBEFORE", (0, 0), (0, -1), 3, edge),
        ("BOX", (0, 0), (-1, -1), 0.35, edge),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return table


def data_table(headers: Iterable[str], rows: Iterable[Iterable[Any]], widths: list[float],
               small: bool = False, repeat: bool = True) -> LongTable:
    cell_style = STYLES["TableCellSmall"] if small else STYLES["TableCell"]
    cooked: list[list[Paragraph]] = [[Paragraph(esc(h), STYLES["TableHead"]) for h in headers]]
    for row in rows:
        cooked.append([
            value if isinstance(value, Paragraph) else Paragraph(str(value), cell_style)
            for value in row
        ])
    table = LongTable(cooked, colWidths=widths, repeatRows=1 if repeat else 0,
                      hAlign="LEFT", splitByRow=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), TEAL_DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("GRID", (0, 0), (-1, -1), 0.35, GRID),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
    ]
    for index in range(1, len(cooked)):
        if index % 2 == 0:
            style.append(("BACKGROUND", (0, index), (-1, index), PAPER))
    table.setStyle(TableStyle(style))
    return table


def bullets(items: Iterable[str]) -> list[Paragraph]:
    return [Paragraph(f"- {item}", STYLES["Bullet"]) for item in items]


def status_chip(text: str, color: Any) -> Table:
    table = Table([[p(f"<b>{esc(text)}</b>", "BodySmall")]], colWidths=[34 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color),
        ("BOX", (0, 0), (-1, -1), 0.4, GRID),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return table


class ManualDocTemplate(BaseDocTemplate):
    def __init__(self, filename: str, **kwargs: Any) -> None:
        super().__init__(filename, **kwargs)
        cover_frame = Frame(20 * mm, 18 * mm, PAGE_W - 40 * mm, PAGE_H - 36 * mm,
                            leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
                            id="cover-frame")
        body_frame = Frame(LEFT, BOTTOM, CONTENT_W, PAGE_H - TOP - BOTTOM,
                           leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
                           id="body-frame")
        self.addPageTemplates([
            PageTemplate(id="cover", frames=[cover_frame], onPage=self._cover_page),
            PageTemplate(id="body", frames=[body_frame], onPage=self._body_page),
        ])

    def _cover_page(self, canvas: Any, doc: Any) -> None:
        canvas.saveState()
        canvas.setTitle("KVerif 新手上手与二次开发手册")
        canvas.setAuthor("KVerif Project")
        canvas.setSubject("KVerif 命令行调用与二次开发参考")
        canvas.setFillColor(TEAL_DARK)
        canvas.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)
        canvas.setFillColor(TEAL)
        canvas.rect(0, 0, 24 * mm, PAGE_H, stroke=0, fill=1)
        canvas.setFillColor(AMBER)
        canvas.rect(24 * mm, PAGE_H - 8 * mm, PAGE_W - 24 * mm, 8 * mm, stroke=0, fill=1)
        canvas.restoreState()

    def _body_page(self, canvas: Any, doc: Any) -> None:
        canvas.saveState()
        canvas.setStrokeColor(GRID)
        canvas.setLineWidth(0.45)
        canvas.line(LEFT, PAGE_H - 12.5 * mm, PAGE_W - RIGHT, PAGE_H - 12.5 * mm)
        canvas.setFont(FONT_BOLD, 7.4)
        canvas.setFillColor(TEAL_DARK)
        canvas.drawString(LEFT, PAGE_H - 9.5 * mm, "KVERIF / 新手上手与二次开发手册")
        canvas.setFont(FONT, 7.2)
        canvas.setFillColor(MUTED)
        canvas.drawRightString(PAGE_W - RIGHT, PAGE_H - 9.5 * mm, f"v{VERSION}  |  {PUBLICATION_DATE}")
        canvas.line(LEFT, 10.5 * mm, PAGE_W - RIGHT, 10.5 * mm)
        canvas.setFont(FONT, 7.2)
        canvas.setFillColor(MUTED)
        canvas.drawString(LEFT, 7 * mm, "二次开发只调用 tools 目录中的命令，不直接调用内部 Tcl/NPI 函数")
        canvas.drawRightString(PAGE_W - RIGHT, 7 * mm, f"{doc.page}")
        canvas.restoreState()

    def afterFlowable(self, flowable: Any) -> None:
        key = getattr(flowable, "_bookmark_name", None)
        if not key:
            return
        text = getattr(flowable, "_heading_text", key)
        outline_level = getattr(flowable, "_outline_level", None)
        toc_level = getattr(flowable, "_toc_level", None)
        self.canv.bookmarkPage(key)
        if outline_level is not None:
            self.canv.addOutlineEntry(text, key, level=outline_level, closed=outline_level >= 1)
        if toc_level is not None:
            self.notify("TOCEntry", (toc_level, text, self.page, key))


def architecture_drawing() -> Drawing:
    width = CONTENT_W
    height = 73 * mm
    d = Drawing(width, height)
    boxes = [
        (5, 142, 150, 34, "Bash / csh / Perl / Python", BLUE_LIGHT, BLUE),
        (185, 142, 150, 34, "MCP 客户端 / AI 客户端", TEAL_LIGHT, TEAL),
        (95, 86, 150, 34, "tools/* 对外命令", AMBER_LIGHT, AMBER),
        (5, 30, 150, 34, "KDebug / KCov 可复用会话", TEAL_LIGHT, TEAL),
        (185, 30, 150, 34, "KBit / KEntry / KLoc / ...", BLUE_LIGHT, BLUE),
    ]
    for x, y, w, h, label, fill, edge in boxes:
        d.add(Rect(x, y, w, h, rx=3, ry=3, fillColor=fill, strokeColor=edge, strokeWidth=0.8))
        d.add(String(x + w / 2, y + 13, label, textAnchor="middle", fontName=FONT_BOLD,
                     fontSize=8.5, fillColor=INK))
    for x1, y1, x2, y2 in [(80, 142, 150, 120), (260, 142, 190, 120), (170, 86, 80, 64), (170, 86, 260, 64)]:
        d.add(Line(x1, y1, x2, y2, strokeColor=MUTED, strokeWidth=1))
    d.add(String(width / 2, 6, "KDebug/KCov 内部调用 Tcl NPI；二次开发脚本只运行命令并读取 JSON。",
                 textAnchor="middle", fontName=FONT, fontSize=7.2, fillColor=MUTED))
    return d


def load_actions() -> list[dict[str, Any]]:
    path = ROOT / "kdebug" / "specs" / "actions" / "actions.yaml"
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [item for item in raw["actions"] if item.get("status") != "removed"]


def inventory_tests() -> dict[str, str]:
    result: dict[str, str] = {}
    text = (ROOT / "kdebug" / "docs" / "action-inventory.md").read_text(encoding="utf-8")
    for line in text.splitlines():
        if not line.startswith("| `"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 6:
            result[cells[0].strip("`")] = cells[-1]
    return result


def choose_example(action: dict[str, Any], kind: str) -> Path | None:
    if kind == "response":
        evidence_dir = ROOT / "kdebug" / "tests" / "vm" / "npi_actions" / "evidence" / "responses"
        evidence_name = (
            "module.objects.parameters.json"
            if action.get("name") == "module.objects"
            else f"{action.get('name', '')}.json"
        )
        evidence_path = evidence_dir / evidence_name
        if evidence_path.exists():
            return evidence_path
    candidates = action.get("examples", {}).get(kind, []) or []
    if not candidates:
        return None
    preferred = next((item for item in candidates if ".basic." in item), candidates[0])
    return ROOT / "kdebug" / preferred


def read_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def infer_type(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    if value is None:
        return "null"
    return "string"


def schema_type(node: dict[str, Any], sample: Any = None) -> str:
    typ = node.get("type")
    if isinstance(typ, list):
        text = " | ".join(str(item) for item in typ)
    elif typ:
        text = str(typ)
    else:
        text = infer_type(sample)
    if text == "array" and isinstance(node.get("items"), dict):
        item_type = node["items"].get("type")
        if item_type:
            text += f"<{item_type}>"
    if node.get("enum"):
        text += " {" + ", ".join(str(item) for item in node["enum"]) + "}"
    if "minimum" in node:
        text += f" >= {node['minimum']}"
    return text


def compact_value(value: Any, depth: int = 0) -> Any:
    if depth >= 3:
        if isinstance(value, (dict, list)):
            return f"<{type(value).__name__}>"
        return value
    if isinstance(value, dict):
        preferred = ["module", "signal", "session_id", "matched_count", "returned", "count", "status"]
        keys = [key for key in preferred if key in value]
        keys += [key for key in value if key not in keys]
        limit = 7 if depth == 0 else 5
        out = {key: compact_value(value[key], depth + 1) for key in keys[:limit]}
        if len(keys) > limit:
            out["_omitted"] = len(keys) - limit
        return out
    if isinstance(value, list):
        if not value:
            return []
        out = [compact_value(value[0], depth + 1)]
        if len(value) > 1:
            out.append(f"... {len(value) - 1} more")
        return out
    if isinstance(value, str) and len(value) > 180:
        return value[:176] + "..."
    return value


def response_excerpt(response: dict[str, Any]) -> str:
    if not response:
        return json.dumps({"ok": True, "note": "response follows the common envelope"}, ensure_ascii=False, indent=2)
    out: dict[str, Any] = {}
    for key in ("api_version", "ok", "action", "request_id"):
        if key in response:
            out[key] = response[key]
    if "summary" in response:
        out["summary"] = compact_value(response["summary"])
    if (not response.get("summary")) and "data" in response:
        out["data"] = compact_value(response["data"])
    if response.get("warnings"):
        out["warnings"] = compact_value(response["warnings"])
    if response.get("error"):
        out["error"] = compact_value(response["error"])
    return json.dumps(out, ensure_ascii=False, indent=2)


def shell_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, (dict, list)):
        raw = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        return "'" + raw.replace("'", "'\"'\"'") + "'"
    raw = str(value)
    if re.fullmatch(r"[A-Za-z0-9_./:@+,-]+", raw):
        return raw
    if "'" in raw and '"' not in raw and not any(char in raw for char in "$`\\"):
        return '"' + raw + '"'
    return "'" + raw.replace("'", "'\"'\"'") + "'"


def action_cli_example(action_name: str, request: dict[str, Any]) -> str:
    lines = [f"{KDEBUG_BIN} --json action {action_name}"]
    target = request.get("target") if isinstance(request.get("target"), dict) else {}
    target_flags = {"daidir": "--daidir", "fsdb": "--fsdb", "session_id": "--session"}
    for key, value in target.items():
        flag = target_flags.get(key)
        if flag:
            lines.append(f"  {flag} {shell_value(value)}")
        else:
            lines.append(f"  --target {shell_value(f'{key}={shell_value(value)}')}" if isinstance(value, str)
                         else f"  --target {shell_value(key + '=' + json.dumps(value, ensure_ascii=False, separators=(',', ':')))}")
    args = request.get("args") if isinstance(request.get("args"), dict) else {}
    for key, value in args.items():
        raw = f"{key}=" + (json.dumps(value, ensure_ascii=False, separators=(",", ":"))
                           if isinstance(value, (dict, list, bool)) or value is None else str(value))
        lines.append(f"  --arg {shell_value(raw)}")
    limits = request.get("limits") if isinstance(request.get("limits"), dict) else {}
    for key, value in limits.items():
        lines.append(f"  --limit {shell_value(f'{key}={value}')}" )
    output = request.get("output") if isinstance(request.get("output"), dict) else {}
    for key, value in output.items():
        raw = json.dumps(value, ensure_ascii=False, separators=(",", ":")) if isinstance(value, (dict, list, bool)) else str(value)
        lines.append(f"  --output {shell_value(key + '=' + raw)}")
    return " \\\n".join(lines)


def sample_text(value: Any) -> str:
    if value is None:
        return "按项目填写"
    if isinstance(value, (dict, list)):
        raw = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        return esc(raw[:180] + ("..." if len(raw) > 180 else ""))
    return esc(value)


def action_param_rows(action: dict[str, Any], request: dict[str, Any]) -> list[tuple[Any, ...]]:
    schema = read_json(ROOT / "kdebug" / action["schemas"]["request"])
    args_schema = schema.get("properties", {}).get("args", {})
    properties = args_schema.get("properties", {}) if isinstance(args_schema, dict) else {}
    required = set(action.get("required_args") or []) | set(args_schema.get("required") or [])
    sample_args = request.get("args") if isinstance(request.get("args"), dict) else {}
    relevant = list(dict.fromkeys(list(required) + list(sample_args)))
    if len(properties) <= 20:
        relevant += [key for key in properties if key not in relevant]
    rows = []
    for key in relevant:
        node = properties.get(key, {}) if isinstance(properties, dict) else {}
        sample = sample_args.get(key)
        rows.append((
            mono(f"args.{key}"),
            esc(schema_type(node, sample)),
            "必填" if key in required else "可选",
            esc(FIELD_DESCRIPTIONS.get(key, "该参数只用于这项操作。可选值和格式见本页字段定义。")),
            sample_text(sample),
        ))
    if not rows:
        rows.append((mono("args"), "object", "可选", "这项操作没有额外的功能参数。", "{}"))
    return rows


def test_label_color(label: str) -> Any:
    lowered = label.lower()
    if "license" in lowered or "blocked" in lowered:
        return AMBER_LIGHT
    if "pass" in lowered or "regression" in lowered or "targeted" in lowered:
        return TEAL_LIGHT
    return PAPER


def kdebug_action_reference(story: list[Any], actions: list[dict[str, Any]], tests: dict[str, str]) -> None:
    category_names = {
        "builtin": "目录与内建",
        "session": "会话生命周期",
        "combined": "设计与波形联合分析",
        "design": "静态设计与 Tcl NPI 模型",
        "waveform": "波形、协议与 FSDB 写出",
    }
    by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for action in actions:
        by_category[action["category"]].append(action)
    order = ["builtin", "session", "combined", "design", "waveform"]
    for category in order:
        items = by_category.get(category, [])
        story.append(heading(category_names[category], 2, f"kdebug-category-{category}"))
        story.append(p(
            f"本节有 <b>{len(items)}</b> 项操作。先通过下表找到需要的操作，再点击名称查看参数和命令。"
            "每项操作都包含：用途、需要的输入、命令示例、输出示例和读取方法。"
        ))
        index_rows = []
        for item in items:
            name = item["name"]
            link = Paragraph(f'<link href="#action-{esc(slug(name))}">{mono(name)}</link>', STYLES["TableCell"])
            index_rows.append((link, esc(item["status"]), esc(item["requires"]), esc(ACTION_PURPOSE.get(name, ""))))
        story.append(data_table(["操作名", "状态", "需要的输入", "用途"], index_rows,
                                [39 * mm, 20 * mm, 22 * mm, CONTENT_W - 81 * mm], small=True))
        story.append(Spacer(1, 6))

        for action in items:
            name = action["name"]
            request_path = choose_example(action, "request")
            response_path = choose_example(action, "response")
            request = read_json(request_path)
            response = read_json(response_path)
            test = tests.get(name, "测试清单中没有标注")

            story.append(CondPageBreak(92 * mm))
            story.append(heading(mono(name), 3, f"action-{slug(name)}", toc=False, outline=True))
            story.append(p(esc(ACTION_PURPOSE.get(name, "按给定参数执行这项操作，并返回 JSON 结果。"))))
            badge = Table([
                [status_chip(f"状态: {action['status']}", TEAL_LIGHT if action["status"] == "stable" else AMBER_LIGHT),
                 status_chip(f"输入: {action['requires']}", BLUE_LIGHT),
                 status_chip(f"实现: {action['handler_kind']}", PAPER)],
            ], colWidths=[CONTENT_W / 3] * 3)
            badge.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
            story.extend([badge, Spacer(1, 4)])
            story.append(callout("验证状态", esc(test), "warn" if "license" in test.lower() else "note"))
            story.append(Spacer(1, 5))
            story.append(p("<b>参数</b>", "H4"))
            story.append(data_table(
                ["参数", "类型/可选值", "是否必填", "说明", "示例值"],
                action_param_rows(action, request),
                [31 * mm, 29 * mm, 15 * mm, 56 * mm, CONTENT_W - 131 * mm],
                small=True,
            ))
            story.append(p(
                f"输入路径、返回数量上限和输出格式见 <link href=\"#kdebug-common-fields\">KDebug 通用参数</link>。"
                f"若要核对程序实际接受的 JSON 字段，可查看 {mono(action['schemas']['request'])}。",
                "BodySmall",
            ))
            story.extend(code_block(action_cli_example(name, request), "命令示例", max_lines=24))
            story.extend(code_block(response_excerpt(response), "标准输出示例", max_lines=24))
            summary_keys = list((response.get("summary") or {}).keys()) if isinstance(response.get("summary"), dict) else []
            key_text = ", ".join(summary_keys[:8]) if summary_keys else "ok、action、data/error"
            story.append(callout(
                "如何读取结果",
                f"先看 {mono('ok')}：{mono('false')} 表示失败，应读取 {mono('error')}；{mono('true')} 表示成功。"
                f"成功后先看 {mono('summary')} 中的 {esc(key_text)}。需要逐项明细时再看 {mono('data')}。"
                f"本页示例取自 {mono(str(response_path.relative_to(ROOT)) if response_path else 'common response format')}。",
                "info",
            ))
            story.append(Spacer(1, 7))


def make_module_instance_demo(story: list[Any]) -> None:
    evidence_dir = ROOT / "kdebug" / "tests" / "vm" / "npi_actions" / "evidence" / "responses"
    find_response = read_json(evidence_dir / "module.find_instances.json")
    inspect_response = read_json(evidence_dir / "module.inspect.json")
    parameter_response = read_json(evidence_dir / "module.objects.parameters.json")
    value_response = read_json(evidence_dir / "language.value.json")

    find_items = find_response.get("data", {}).get("instances", [])
    instance_object = (find_items[0].get("object", {}) if find_items else {})
    parameter_items = parameter_response.get("data", {}).get("items", [])
    parameter_rows = []
    for item in parameter_items:
        obj = item.get("object", {})
        values = item.get("values", {})
        parameter_rows.append((
            mono(obj.get("name", "")),
            mono(obj.get("full_name", "")),
            esc("localparam" if obj.get("local_param") else "parameter"),
            esc(obj.get("size", "")),
            mono(values.get("dec", "")),
            mono(values.get("hex", "")),
        ))

    story.append(heading(
        "演示：查找模块实例和实际参数值",
        2,
        "kdebug-module-instance-demo",
    ))
    story.append(p(
        "本节演示一个常见问题：已知模块定义名，怎样找到它在设计中的所有实例，并读取每个实例真正采用的参数值。"
        "整个过程分为四步。先找实例路径，再查看实例内容，然后列出全部 parameter/localparam，最后读取某一个参数。"
        "示例来自 2026-07-29 普通用户 host 的 Verdi "
        "O-2018.09-SP2 VM 实测结果。"
    ))
    story.append(callout(
        "先区分三个名字",
        f"模块定义名是 {mono('npi_fixture_alu')}；实例层次全路径是 {mono('npi_fixture_top.u_alu')}；"
        f"实例中 WIDTH 参数的完整路径是 {mono('npi_fixture_top.u_alu.WIDTH')}。"
        "这三个名称用途不同，后面的命令不能混着填。",
        "info",
    ))
    story.append(Spacer(1, 5))
    story.append(data_table(["阶段", "输入", "操作", "关键输出"], [
        ("1. 定义 -> 实例", mono("definition=npi_fixture_alu"), mono("module.find_instances"), mono("npi_fixture_top.u_alu")),
        ("2. 查看实例", mono("module=npi_fixture_top.u_alu"), mono("module.inspect"), "参数、端口、连线等内容"),
        ("3. 列出全部参数", mono("kind=parameters"), mono("module.objects"), "WIDTH、BIAS、RESULT_WIDTH 的实际值"),
        ("4. 读取单值", mono("name=...u_alu.WIDTH"), mono("language.value"), mono("value=12")),
    ], [32 * mm, 56 * mm, 44 * mm, CONTENT_W - 132 * mm], small=True))

    story.append(heading("先看示例 RTL", 3, "module-demo-rtl", toc=False, outline=True))
    story.extend(code_block("""module npi_fixture_alu #(
  parameter int WIDTH = 8,
  parameter logic [WIDTH-1:0] BIAS = '0
) (...);
  localparam int RESULT_WIDTH = WIDTH;
endmodule

module npi_fixture_top;
  localparam int WIDTH = 12;
  npi_fixture_alu #(
    .WIDTH(WIDTH),
    .BIAS(12'h001)
  ) u_alu (...);
endmodule""", "压测所用 RTL 摘录"))
    bias_default = mono("BIAS='0")
    story.append(callout(
        "默认值和实例实际值不同",
        f"模块定义中的默认值是 {mono('WIDTH=8')}、{bias_default}；实例覆盖参数后，VM 实测值变为 "
        f"{mono('WIDTH=12')}、{mono('BIAS=1')}，并推导出 {mono('RESULT_WIDTH=12')}。"
        "分析具体实例时，应使用工具返回的实例实际值，而不能只看模块定义中的默认值。",
        "warn",
    ))

    daidir = "/home/host/kverif_npi_action_stress_20260729/fixture/design/simv.daidir"
    story.append(CondPageBreak(70 * mm))
    story.append(heading("第 1 步：根据定义查全部例化路径", 3, "module-demo-find", toc=False, outline=True))
    story.extend(code_block(
        f"""KDEBUG=/home/host/kverif/tools/kdebug
DAIDIR={daidir}

$KDEBUG --json action module.find_instances \\
  --daidir \"$DAIDIR\" \\
  --arg definition=npi_fixture_alu \\
  --limit max_rows=100 > /tmp/module.find_instances.json""",
        "命令",
    ))
    find_excerpt = {
        "ok": find_response.get("ok"),
        "action": find_response.get("action"),
        "summary": find_response.get("summary"),
        "data": {"instances": [{"object": {
            key: instance_object.get(key)
            for key in ("name", "full_name", "type", "def_name", "line", "def_line")
        }}]},
    }
    story.extend(code_block(json.dumps(find_excerpt, ensure_ascii=False, indent=2), "VM 实测输出摘录"))
    story.append(p(
        f"读取 {mono('data.instances[*].object.full_name')}。本例返回一条路径 "
        f"{mono(instance_object.get('full_name', 'npi_fixture_top.u_alu'))}。如果 count 大于 1，脚本必须逐实例分析，不能只取第一项。"
    ))

    story.append(heading("第 2 步：一次检查实例、parameter 和端口", 3, "module-demo-inspect", toc=False, outline=True))
    story.extend(code_block(
        """$KDEBUG --json action module.inspect \\
  --daidir "$DAIDIR" \\
  --arg module=npi_fixture_top.u_alu \\
  --arg 'sections=["parameters","ports","io","nets","variables"]' \\
  --limit max_rows=100 > /tmp/module.inspect.json""",
        "命令",
    ))
    inspect_summary = inspect_response.get("summary", {})
    inspect_excerpt = {
        "ok": inspect_response.get("ok"),
        "action": inspect_response.get("action"),
        "summary": inspect_summary,
        "data": {
            "module": inspect_response.get("data", {}).get("module"),
            "parameter_values": {
                item.get("object", {}).get("name"): item.get("values", {}).get("dec")
                for item in inspect_response.get("data", {}).get("sections", {}).get("parameters", [])
            },
        },
    }
    story.extend(code_block(json.dumps(inspect_excerpt, ensure_ascii=False, indent=2), "VM 实测输出摘录"))
    story.append(p(
        f"本次实测返回 {mono('parameters=3')}、{mono('ports=3')}、{mono('io=3')}，且 "
        f"{mono('truncated=false')}。如果想一次查看实例的参数和端口，优先使用这条命令。"
    ))

    story.append(heading("第 3 步：列出全部 parameter 和 localparam", 3, "module-demo-parameters", toc=False, outline=True))
    story.extend(code_block(
        """$KDEBUG --json action module.objects \\
  --daidir "$DAIDIR" \\
  --arg module=npi_fixture_top.u_alu \\
  --arg kind=parameters \\
  --limit max_rows=100 > /tmp/module.parameters.json""",
        "命令",
    ))
    story.append(data_table(
        ["名称", "对象全路径", "类别", "宽度", "dec", "hex"],
        parameter_rows,
        [24 * mm, 63 * mm, 24 * mm, 16 * mm, 17 * mm, CONTENT_W - 144 * mm],
        small=True,
    ))
    story.append(p(
        f"表中数值直接来自 VM 测试结果文件 {mono('kdebug/tests/vm/npi_actions/evidence/responses/module.objects.parameters.json')}。"
        f"其中 {mono('local_param=1')} 表示 {mono('RESULT_WIDTH')} 是实例内部定义的 localparam。"
    ))

    story.append(heading("第 4 步：精确读取一个 parameter 值", 3, "module-demo-value", toc=False, outline=True))
    story.extend(code_block(
        """$KDEBUG --json action language.value \\
  --daidir "$DAIDIR" \\
  --arg name=npi_fixture_top.u_alu.WIDTH \\
  --arg format=npiDecStrVal > /tmp/u_alu.WIDTH.json""",
        "命令",
    ))
    value_data = value_response.get("data", {})
    value_excerpt = {
        "ok": value_response.get("ok"),
        "action": value_response.get("action"),
        "data": {key: value_data.get(key) for key in ("name", "type", "format", "value", "size", "signed")},
    }
    story.extend(code_block(json.dumps(value_excerpt, ensure_ascii=False, indent=2), "VM 实测输出摘录"))

    story.append(heading("自动化：遍历所有实例并生成结论", 3, "module-demo-automation", toc=False, outline=True))
    story.extend(code_block("""#!/usr/bin/env python3
import json, subprocess

KDEBUG = "/home/host/kverif/tools/kdebug"
DAIDIR = "/proj/out/simv.daidir"

def query(action, *args):
    cmd = [KDEBUG, "--json", "action", action, "--daidir", DAIDIR]
    for item in args:
        cmd += ["--arg", item]
    rsp = json.loads(subprocess.run(cmd, check=True, text=True,
                                    capture_output=True).stdout)
    if not rsp.get("ok") or rsp.get("summary", {}).get("truncated"):
        raise RuntimeError(rsp.get("error") or "incomplete KDebug result")
    return rsp

found = query("module.find_instances", "definition=npi_fixture_alu")
report = []
for row in found["data"]["instances"]:
    path = row["object"]["full_name"]
    params = query("module.objects", "module=" + path, "kind=parameters")
    report.append({
        "instance": path,
        "definition": row["object"]["def_name"],
        "parameters": {item["object"]["name"]: item["values"]["dec"]
                       for item in params["data"]["items"]},
    })
print(json.dumps({"instance_count": len(report), "instances": report},
                 indent=2, sort_keys=True))""", "Python 二次开发示例", max_lines=38))
    story.extend(code_block("""{
  "instance_count": 1,
  "instances": [{
    "definition": "npi_fixture_alu",
    "instance": "npi_fixture_top.u_alu",
    "parameters": {"BIAS": "1", "RESULT_WIDTH": "12", "WIDTH": "12"}
  }]
}""", "脚本输出"))

    story.append(heading("迁移到自己的设计", 3, "module-demo-adapt", toc=False, outline=True))
    story.append(data_table(["需要替换", "如何获得", "注意事项"], [
        (mono("DAIDIR"), "VCS 编译生成的 simv.daidir 绝对路径", "必须对应当前要分析的、已经编译展开的设计。"),
        (mono("definition"), "RTL module 定义名", "它不是层次路径。"),
        (mono("module"), mono("module.find_instances"), "使用返回的 full_name，多个实例逐项处理。"),
        (mono("kind=parameters"), "固定枚举值", "读取 parameter/localparam；其他对象使用对应 kind。"),
        (mono("max_rows"), "按设计规模设置", "始终检查 truncated=false。"),
    ], [40 * mm, 58 * mm, CONTENT_W - 98 * mm]))
    story.append(callout(
        "VM 实测结果",
        f"{mono('module.find_instances')} 10/10 PASS；{mono('module.inspect')} 10/10 PASS；"
        f"{mono('module.objects(kind=parameters)')} 10/10 PASS；{mono('language.value')} 10/10 PASS。"
        "实测断言明确校验 WIDTH=12、BIAS=1、RESULT_WIDTH=12。",
        "note",
    ))
    story.append(p(
        f"各返回字段的完整说明见 <link href=\"#action-module.find_instances\">module.find_instances</link>、"
        f"<link href=\"#action-module.inspect\">module.inspect</link>、"
        f"<link href=\"#action-module.objects\">module.objects</link> 和 "
        f"<link href=\"#action-language.value\">language.value</link>。"
    ))


def npi_vm_response(name: str) -> dict[str, Any]:
    return read_json(ROOT / "kdebug" / "tests" / "vm" / "npi_actions" / "evidence" / "responses" / f"{name}.json")


def response_items(response: dict[str, Any], key: str = "items") -> list[dict[str, Any]]:
    value = response.get("data", {}).get(key, [])
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [value]
    return []


def make_task_coverage_audit(story: list[Any]) -> None:
    story.append(heading("本手册覆盖哪些常用 NPI 任务", 2, "kdebug-task-coverage"))
    story.append(p(
        "实际工作通常要连续执行几项操作。例如，要读取某个实例的实际参数值，需要先根据模块定义找到实例路径，"
        "再查询这个实例的 parameter。下表列出本手册已经完整演示的常用任务。"
    ))
    story.append(callout(
        "本版检查范围",
        f"手册覆盖 {len(NPI_WORKFLOW_ACTIONS)} 项 NPI 操作、{len(MODULE_OBJECT_KINDS)} 类模块对象和 "
        f"{len(WORKFLOW_COVERAGE)} 个常用任务。每个任务都有可直接执行的命令、关键输出、字段说明和 VM 测试结果。",
        "warn",
    ))
    rows = []
    for item in WORKFLOW_COVERAGE:
        rows.append((
            esc(item["task"]),
            esc(" -> ".join(item["actions"])),
            esc("、".join(item["kinds"]) if item["kinds"] else "不适用"),
            esc(item["evidence"]),
        ))
    story.append(data_table(
        ["用户任务", "操作顺序", "module.objects 类别", "VM 测试情况"],
        rows,
        [38 * mm, 76 * mm, 42 * mm, CONTENT_W - 156 * mm],
        small=True,
    ))
    story.append(p(
        "下面先讲这些常用 NPI 任务。波形、协议、覆盖率和其他工具的用法，请查看后面的命令说明和"
        "“脚本怎样调用 KVerif”章节。"
    ))


def make_ports_connectivity_demo(story: list[Any]) -> None:
    ports_response = npi_vm_response("module.objects.ports")
    io_response = npi_vm_response("module.objects.io")
    relation_response = npi_vm_response("language.relate")
    ports = response_items(ports_response)
    port_rows = []
    unconnected = []
    width_mismatch = []
    for item in ports:
        obj = item.get("object", {})
        conns = item.get("connections", {})
        high = conns.get("high") or {}
        low = conns.get("low") or {}
        if not high and not low:
            unconnected.append(obj.get("full_name", ""))
        sizes = {value for value in (obj.get("size"), high.get("size"), low.get("size")) if value is not None}
        if len(sizes) > 1:
            width_mismatch.append(obj.get("full_name", ""))
        port_rows.append((
            mono(obj.get("name", "")), mono(obj.get("direction", "")), esc(obj.get("size", "")),
            mono(high.get("full_name", "")), mono(low.get("full_name", "")),
        ))

    story.append(heading(
        "演示：模块端口、方向、位宽与上下层连线",
        2,
        "kdebug-port-connectivity-demo",
    ))
    story.append(p(
        "检查模块端口时，只有端口名还不够。至少还要知道方向、编译展开后的实际位宽、端口序号、上层连接字段 "
        f"{mono('npiHighConn')} 和实例内部连接字段 {mono('npiLowConn')}。本例继续使用实例 "
        f"{mono('npi_fixture_top.u_alu')}。"
    ))
    story.extend(code_block("""KDEBUG=/home/host/kverif/tools/kdebug
DAIDIR=/home/host/kverif_npi_action_stress_20260729/fixture/design/simv.daidir

$KDEBUG --json action module.objects \\
  --daidir "$DAIDIR" \\
  --arg module=npi_fixture_top.u_alu \\
  --arg kind=ports \\
  --limit max_rows=100 > /tmp/u_alu.ports.json""", "命令"))
    story.append(data_table(
        ["port", "direction", "width", "high connection", "low connection"],
        port_rows,
        [20 * mm, 24 * mm, 14 * mm, 61 * mm, CONTENT_W - 119 * mm],
        small=True,
    ))
    story.append(callout(
        "什么时候用 ports，什么时候用 io",
        f"{mono('kind=ports')} 返回端口对象、端口序号、位宽以及上下层连接，适合检查模块连线；"
        f"{mono('kind=io')} 返回 RTL 中的输入输出声明和方向。VM 实测两者均返回 3 项："
        f"{mono('lhs/rhs=npiInput')}，{mono('result=npiOutput')}。",
        "info",
    ))
    relation_data = relation_response.get("data", {})
    related = relation_data.get("object", {}).get("object", {})
    story.append(heading("精确读取一个端口关系", 3, "port-demo-relate", toc=False, outline=True))
    story.extend(code_block("""$KDEBUG --json action language.relate \\
  --daidir "$DAIDIR" \\
  --arg name=npi_fixture_top.u_alu.result \\
  --arg relation_type=npiHighConn > /tmp/u_alu.result.high.json""", "命令"))
    relation_excerpt = {
        "ok": relation_response.get("ok"),
        "source": relation_data.get("source"),
        "relation_type": relation_data.get("relation_type"),
        "related": {key: related.get(key) for key in ("full_name", "type", "size", "line")},
    }
    story.extend(code_block(json.dumps(relation_excerpt, ensure_ascii=False, indent=2), "VM 实测输出摘录"))
    conclusion = {
        "module": "npi_fixture_top.u_alu",
        "port_count": len(ports),
        "io_declaration_count": len(response_items(io_response)),
        "unconnected_ports": unconnected,
        "width_mismatches": width_mismatch,
        "result_high_connection": related.get("full_name"),
        "status": "PASS" if not unconnected and not width_mismatch else "REVIEW",
    }
    story.extend(code_block(json.dumps(conclusion, ensure_ascii=False, indent=2), "脚本检查结果"))
    story.append(p(
        "在自己的设计中，不要因为 high/low 连接字段非空就认定连线正确。脚本还应检查方向规则、位宽是否一致、"
        "允许悬空的白名单以及 interface/modport 语义。详细字段见 "
        "<link href=\"#action-module.objects\">module.objects</link>、"
        "<link href=\"#action-module.inspect\">module.inspect</link> 和 "
        "<link href=\"#action-language.relate\">language.relate</link>。"
    ))
    story.append(callout(
        "VM 实测结果",
        "module.objects(kind=ports) 10/10 PASS；module.objects(kind=io) 10/10 PASS；language.relate 10/10 PASS。",
        "note",
    ))


def make_hierarchy_demo(story: list[Any]) -> None:
    kinds = ["instances", "generate_scopes", "instances_in_generate", "primitives"]
    responses = {kind: npi_vm_response(f"module.objects.{kind}") for kind in kinds}
    rows = []
    conclusion: dict[str, Any] = {}
    for kind in kinds:
        names = []
        for item in response_items(responses[kind]):
            obj = item.get("object", {})
            names.append(obj.get("full_name", ""))
            rows.append((
                mono(kind), mono(obj.get("full_name", "")), mono(obj.get("type", "")),
                mono(obj.get("def_name", "")), esc(obj.get("line", "")),
            ))
        conclusion[kind] = names
    conclusion["instantiated_unit_count"] = sum(len(conclusion[kind]) for kind in ("instances", "instances_in_generate", "primitives"))

    story.append(heading(
        "演示：列出普通实例、generate 实例和 primitive",
        2,
        "kdebug-hierarchy-demo",
    ))
    story.append(p(
        f"只执行 {mono('kind=instances')} 会漏掉 generate scope 内的实例和 Verilog primitive。"
        "要完整列出层次，至少应查询下面四种 kind，并保留每项的模块定义名、源码行和完整层次名。"
    ))
    story.extend(code_block("""KDEBUG=/home/host/kverif/tools/kdebug
DAIDIR=/home/host/kverif_npi_action_stress_20260729/fixture/design/simv.daidir

for KIND in instances generate_scopes instances_in_generate primitives; do
  $KDEBUG --json action module.objects \\
    --daidir "$DAIDIR" \\
    --arg module=npi_fixture_top \\
    --arg kind="$KIND" \\
    --limit max_rows=100 > "/tmp/top.$KIND.json" || exit 2
done""", "完整查询命令"))
    story.append(data_table(
        ["kind", "完整层次路径", "object type", "definition", "line"],
        rows,
        [34 * mm, 58 * mm, 26 * mm, 34 * mm, CONTENT_W - 152 * mm],
        small=True,
    ))
    story.extend(code_block(json.dumps(conclusion, ensure_ascii=False, indent=2), "合并后的层次结论"))
    story.append(callout(
        "本例为什么必须查四次",
        f"普通实例是 {mono('npi_fixture_top.u_alu')}；generate 形成的层次是 {mono('npi_fixture_top.g_wide')}；"
        f"该层次里的实例是 {mono('npi_fixture_top.g_wide.u_leaf')}；primitive 是 {mono('npi_fixture_top.u_not')}。"
        "generate scope 只是一个层次容器，并不是模块实例。统计实例数量时不要把它重复计算。",
        "warn",
    ))
    story.append(p(
        "如果要“根据模块定义名找所有实例”，使用 "
        "<link href=\"#action-module.find_instances\">module.find_instances</link>；"
        "如果要“列出某个父模块下的所有子对象”，则合并上述几种 "
        "<link href=\"#action-module.objects\">module.objects</link> 查询结果。"
    ))
    story.append(callout(
        "VM 实测结果",
        "instances、generate_scopes、instances_in_generate、primitives 四个 kind 均为 10/10 PASS。",
        "note",
    ))


def make_internal_objects_demo(story: list[Any]) -> None:
    specs = [
        ("nets", "npi_fixture_top"),
        ("variables", "npi_fixture_top.u_alu"),
        ("functions", "npi_fixture_top.u_alu"),
        ("tasks", "npi_fixture_top"),
        ("continuous_assignments", "npi_fixture_top.u_alu"),
        ("always_processes", "npi_fixture_top.u_alu"),
        ("initial_processes", "npi_fixture_top"),
        ("language_interfaces", "npi_fixture_top"),
    ]
    rows = []
    conclusion: dict[str, Any] = {}
    for kind, module_name in specs:
        response = npi_vm_response(f"module.objects.{kind}")
        items = response_items(response)
        first = items[0].get("object", {}) if items else {}
        count = response.get("summary", {}).get("count", len(items))
        example = first.get("full_name") or first.get("type") or "(测试设计中没有这类对象)"
        rows.append((
            mono(kind), mono(module_name), esc(count), mono(example) if first else esc(example), esc(first.get("line", "")),
        ))
        conclusion[kind] = {
            "count": count,
            "example": example,
            "line": first.get("line"),
        }

    line_response = npi_vm_response("text.line")
    line_data = line_response.get("data", {})
    story.append(heading(
        "演示：模块内部对象、过程与源码位置",
        2,
        "kdebug-internal-objects-demo",
    ))
    story.append(p(
        "查看模块内部内容时，可以先分成两类：net、variable、function、task 是声明或可调用对象；"
        "连续赋值、always、initial 是描述行为的语句块。每个返回对象都带 file 和 line，随后可用 text.line 读取源码。"
    ))
    story.extend(code_block("""KDEBUG=/home/host/kverif/tools/kdebug
DAIDIR=/home/host/kverif_npi_action_stress_20260729/fixture/design/simv.daidir

query_kind() {
  MODULE=$1; KIND=$2
  $KDEBUG --json action module.objects --daidir "$DAIDIR" \\
    --arg "module=$MODULE" --arg "kind=$KIND" --limit max_rows=100 \\
    > "/tmp/${KIND}.json" || return 2
}

query_kind npi_fixture_top       nets
query_kind npi_fixture_top.u_alu variables
query_kind npi_fixture_top.u_alu functions
query_kind npi_fixture_top       tasks
query_kind npi_fixture_top.u_alu continuous_assignments
query_kind npi_fixture_top.u_alu always_processes
query_kind npi_fixture_top       initial_processes
query_kind npi_fixture_top       language_interfaces""", "完整查询命令", max_lines=30))
    story.append(data_table(
        ["kind", "module", "count", "VM 返回示例", "line"],
        rows,
        [37 * mm, 45 * mm, 14 * mm, 63 * mm, CONTENT_W - 159 * mm],
        small=True,
    ))
    story.append(callout(
        "零结果也必须被正确解释",
        f"测试设计中没有 SystemVerilog interface，因此 {mono('language_interfaces')} 返回 "
        f"{mono('count=0, truncated=false')}。这表示命令执行成功，只是没有找到这类对象。"
        f"只有出现 {mono('ok=false')}、error，或结果被截短时，脚本才不能继续给出完整结论。",
        "info",
    ))
    story.append(heading("从行为对象跳到源码行", 3, "internal-demo-source", toc=False, outline=True))
    story.extend(code_block("""SOURCE=$(python3 -c \\
  'import json; r=json.load(open("/tmp/always_processes.json")); \\
print(r["data"]["items"][0]["object"]["file"])')

$KDEBUG --json action text.line --daidir "$DAIDIR" \\
  --arg "file=$SOURCE" --arg line=27 > /tmp/source.line27.json""", "命令"))
    line_excerpt = {
        "ok": line_response.get("ok"),
        "line": line_data.get("line"),
        "content": line_data.get("content", "").rstrip("\n"),
        "word_count": line_data.get("word_count"),
    }
    story.extend(code_block(json.dumps(line_excerpt, ensure_ascii=False, indent=2), "VM 实测输出摘录"))
    story.extend(code_block(json.dumps({
        "module": "npi_fixture_top.u_alu",
        "variable": "sum@17",
        "function": "add_with_bias@19",
        "always_process": "npiAlways@26",
        "assignment_line": "sum = add_with_bias(lhs, rhs);",
        "continuous_assignment": "npiContAssign@30",
    }, ensure_ascii=False, indent=2), "脚本整理后的结果"))
    story.append(p(
        "这组命令可以生成模块内容清单、定位组合逻辑入口、检查 task/function 是否存在，并从 NPI 查询结果跳到"
        "对应源码。详细字段见 <link href=\"#action-module.objects\">module.objects</link> 和 "
        "<link href=\"#action-text.line\">text.line</link>。"
    ))
    story.append(callout(
        "VM 实测结果",
        "上述 8 个 module.objects kind 与 text.line 均为 10/10 PASS；其中 language_interfaces 的正确结果为 0 项。",
        "note",
    ))


def make_language_netlist_demo(story: list[Any]) -> None:
    language_resolve = npi_vm_response("language.resolve")
    language_iterate = npi_vm_response("language.iterate")
    language_relate = npi_vm_response("language.relate")
    netlist_resolve = npi_vm_response("netlist.resolve")
    netlist_iterate = npi_vm_response("netlist.iterate")

    language_object = language_resolve.get("data", {}).get("object", {}).get("object", {})
    related_object = language_relate.get("data", {}).get("object", {}).get("object", {})
    netlist_object = netlist_resolve.get("data", {}).get("object", {})
    story.append(heading(
        "演示：对照 RTL 设计对象和展开后的网表对象",
        2,
        "kdebug-language-netlist-demo",
    ))
    story.append(p(
        "NPI Language Model 看到的是 RTL 里的模块、参数、端口、源码行和对象关系；NPI Netlist Model 看到的是"
        "编译展开后的 net、cell 和位切片。两者回答的问题不同：查层次、参数和源码时先用 language.*；"
        "查位切片、门级对象或网表名称时先用 netlist.*。"
    ))
    story.extend(code_block("""KDEBUG=/home/host/kverif/tools/kdebug
DAIDIR=/home/host/kverif_npi_action_stress_20260729/fixture/design/simv.daidir

$KDEBUG --json action language.resolve --daidir "$DAIDIR" \\
  --arg name=npi_fixture_top.u_alu > /tmp/language.instance.json

$KDEBUG --json action language.iterate --daidir "$DAIDIR" \\
  --arg name=npi_fixture_top.u_alu --arg object_type=npiParameter \\
  --limit max_rows=100 > /tmp/language.parameters.json

$KDEBUG --json action netlist.resolve --daidir "$DAIDIR" \\
  --arg name=npi_fixture_top.result --arg object_type=npiNlNet \\
  > /tmp/netlist.result.json

$KDEBUG --json action netlist.iterate --daidir "$DAIDIR" \\
  --arg name=npi_fixture_top --arg object_type=npiNlNet \\
  --limit max_rows=100 > /tmp/netlist.nets.json""", "两类对象的查询命令", max_lines=30))
    comparison_rows = [
        ("Language resolve", mono(language_object.get("full_name", "")), mono(language_object.get("type", "")),
         mono(language_object.get("def_name", "")), esc(language_object.get("line", "")), "实例、定义与源码"),
        ("Language iterate", mono("WIDTH / BIAS / RESULT_WIDTH"), mono("npiParameter"),
         mono("12 / 1 / 12"), "9/10/16", "实际参数与 localparam"),
        ("Language relate", mono(related_object.get("full_name", "")), mono(related_object.get("type", "")),
         mono(related_object.get("size", "")), esc(related_object.get("line", "")), "RTL 端口上下层关系"),
        ("Netlist resolve", mono(netlist_object.get("full_name", "")), mono(netlist_object.get("type", "")),
         mono(netlist_object.get("size", "")), "不适用", "编译展开后的总线或位切片"),
        ("Netlist iterate", mono("7 nets"), mono("npiNlNet"), mono("result[11:0]"), "不适用", "网表对象全集"),
    ]
    story.append(data_table(
        ["查询", "关键对象", "type", "定义/数值/宽度", "line", "适合回答"],
        comparison_rows,
        [29 * mm, 48 * mm, 31 * mm, 31 * mm, 16 * mm, CONTENT_W - 155 * mm],
        small=True,
    ))
    language_names = [item.get("object", {}).get("name") for item in response_items(language_iterate)]
    netlist_names = [item.get("full_name") for item in response_items(netlist_iterate) if item.get("full_name")]
    story.extend(code_block(json.dumps({
        "language_instance": language_object.get("full_name"),
        "definition": language_object.get("def_name"),
        "language_parameters": language_names,
        "rtl_high_connection": related_object.get("full_name"),
        "netlist_resolved_name": netlist_object.get("full_name"),
        "netlist_width": netlist_object.get("size"),
        "netlist_contains_result": "npi_fixture_top.result[11:0]" in netlist_names,
    }, ensure_ascii=False, indent=2), "对照后的结果"))
    story.append(callout(
        "不要自行改写工具返回的名称",
        f"RTL 连接名是 {mono('npi_fixture_top.result')}，Netlist Model 返回 "
        f"{mono('npi_fixture_top.result[11:0]')}。脚本应同时保存对象来自哪种 NPI 模型，以及 type、size 和原始 full_name。"
        "不要先删除 [11:0]，再假定两个名称一定指向同一类对象。",
        "warn",
    ))
    story.append(p(
        "详细字段见 <link href=\"#action-language.resolve\">language.resolve</link>、"
        "<link href=\"#action-language.iterate\">language.iterate</link>、"
        "<link href=\"#action-language.relate\">language.relate</link>、"
        "<link href=\"#action-netlist.resolve\">netlist.resolve</link> 和 "
        "<link href=\"#action-netlist.iterate\">netlist.iterate</link>。"
    ))
    story.append(callout(
        "VM 实测结果",
        "language.resolve/iterate/relate 与 netlist.resolve/iterate 五项均为 10/10 PASS。",
        "note",
    ))


def make_source_modification_demo(story: list[Any]) -> None:
    line_response = npi_vm_response("text.line")
    words_response = npi_vm_response("text.words")
    replace_response = npi_vm_response("text.replace_line")
    add_response = npi_vm_response("dm.add_net")
    clone_response = npi_vm_response("dm.clone_module")
    line_data = line_response.get("data", {})
    word_rows = []
    for item in words_response.get("data", {}).get("words", []):
        text_value = item.get("text", "")
        if text_value.strip() in {"sum", "add_with_bias", "lhs", "rhs", "="}:
            word_rows.append((esc(item.get("index", "")), mono(text_value), mono(item.get("attribute", ""))))

    story.append(heading(
        "演示：读取源码并在副本中修改设计",
        2,
        "kdebug-source-modification-demo",
    ))
    story.append(p(
        "text.line 和 text.words 用来读取编译数据库对应的源码行及其中的单词、符号；dm.add_net 和 dm.clone_module "
        "会生成修改后的设计文件。所有修改都写到新路径，不会直接覆盖原 RTL。生成文件后，仍要执行 diff、重新编译和回归。"
    ))
    story.extend(code_block("""KDEBUG=/home/host/kverif/tools/kdebug
DAIDIR=/home/host/kverif_npi_action_stress_20260729/fixture/design/simv.daidir
OUT=/tmp/kverif-npi-demo
mkdir -p "$OUT"

$KDEBUG --json action module.objects --daidir "$DAIDIR" \\
  --arg module=npi_fixture_top.u_alu --arg kind=always_processes \\
  --limit max_rows=100 > "$OUT/always.json"
SOURCE=$(python3 -c \\
  'import json,sys; print(json.load(open(sys.argv[1]))["data"]["items"][0]["object"]["file"])' \\
  "$OUT/always.json")

$KDEBUG --json action text.line --daidir "$DAIDIR" \\
  --arg "file=$SOURCE" --arg line=27 > "$OUT/line.json"

$KDEBUG --json action text.words --daidir "$DAIDIR" \\
  --arg "file=$SOURCE" --arg line=27 --limit max_rows=100 \\
  > "$OUT/words.json"

$KDEBUG --json action text.replace_line --daidir "$DAIDIR" \\
  --arg "file=$SOURCE" --arg line=27 \\
  --arg 'content=    sum = lhs - rhs;' \\
  --arg "output=$OUT/design.patched.sv" > "$OUT/replace.json""", "Text Model 命令", max_lines=30))
    story.extend(code_block(json.dumps({
        "line": line_data.get("line"),
        "content": line_data.get("content", "").rstrip("\n"),
        "word_count": line_data.get("word_count"),
    }, ensure_ascii=False, indent=2), "text.line 的 VM 输出摘录"))
    story.append(data_table(["序号", "单词或符号", "NPI 返回的属性"], word_rows,
                            [24 * mm, 54 * mm, CONTENT_W - 78 * mm], small=True))
    replace_data = replace_response.get("data", {})
    story.extend(code_block(json.dumps({
        "status": replace_response.get("summary", {}).get("status"),
        "line": replace_data.get("line"),
        "original": replace_data.get("original", "").rstrip("\n"),
        "replacement": replace_data.get("replacement"),
        "output": "/tmp/kverif-npi-demo/design.patched.sv",
    }, ensure_ascii=False, indent=2), "text.replace_line 输出"))
    story.append(callout(
        "源码路径应以编译数据库返回的结果为准",
        "在自己的项目中，应从 module.objects 或 language.resolve 返回的 object.file 读取源码完整路径。"
        "如果 daidir 是在另一个工作区编译出来的，不要凭目录结构猜 SOURCE。应使用数据库返回的路径，"
        "或重新生成与当前源码目录一致的 daidir。",
        "warn",
    ))

    story.append(heading("生成修改后的设计文本", 3, "source-demo-dm", toc=False, outline=True))
    story.extend(code_block("""$KDEBUG --json action dm.add_net --daidir "$DAIDIR" \\
  --arg module=npi_fixture_top --arg name=debug_bus \\
  --arg net_type=npiDmNetWire --arg packed_left=7 --arg packed_right=0 \\
  --arg "output_dir=$OUT/dm-add-net" > "$OUT/dm-add-net.json"

$KDEBUG --json action dm.clone_module --daidir "$DAIDIR" \\
  --arg module=npi_fixture_alu --arg new_name=npi_fixture_alu_clone \\
  --arg "output_dir=$OUT/dm-clone" > "$OUT/dm-clone.json"

diff -u "$SOURCE" "$OUT/design.patched.sv" || test $? -eq 1""", "生成设计副本的命令"))
    add_data = add_response.get("data", {})
    clone_data = clone_response.get("data", {})
    result_rows = [
        (mono("text.replace_line"), "written", mono("design.patched.sv"), "第 27 行替换；原文件不变"),
        (mono("dm.add_net"), esc(add_response.get("summary", {}).get("status")),
         mono(add_data.get("name", "")), f"{add_data.get('net_type')} [{add_data.get('packed_left')}:{add_data.get('packed_right')}]"),
        (mono("dm.clone_module"), esc(clone_response.get("summary", {}).get("status")),
         mono(clone_data.get("new_name", "")), "在独立目录中生成复制后的模块"),
    ]
    story.append(data_table(["操作", "状态", "生成文件或对象", "实际结果"], result_rows,
                            [42 * mm, 24 * mm, 54 * mm, CONTENT_W - 120 * mm], small=True))
    story.append(callout(
        "接受修改前必须完成这些检查",
        "先确认 ok=true 且输出文件非空；再确认输出路径不是原文件；随后执行 diff、重新编译和目标回归。"
        "KDebug 返回 written 只表示文件已经写出，不表示 RTL 功能正确。",
        "warn",
    ))
    story.append(p(
        "详细字段见 <link href=\"#action-text.line\">text.line</link>、"
        "<link href=\"#action-text.words\">text.words</link>、"
        "<link href=\"#action-text.replace_line\">text.replace_line</link>、"
        "<link href=\"#action-dm.add_net\">dm.add_net</link> 和 "
        "<link href=\"#action-dm.clone_module\">dm.clone_module</link>。"
    ))
    story.append(callout(
        "VM 实测结果",
        "text.line/words/replace_line 与 dm.add_net/clone_module 五项均为 10/10 PASS，输出文件非空且内容断言通过。",
        "note",
    ))


def make_environment_crdb_demo(story: list[Any]) -> None:
    capabilities = npi_vm_response("npi.capabilities")
    vcs_response = npi_vm_response("vcs.summary")
    crdb_resolve = npi_vm_response("crdb.resolve")
    crdb_correlates = npi_vm_response("crdb.correlates")
    vcs_data = vcs_response.get("data", {})
    crdb_object = crdb_resolve.get("data", {}).get("object", {})
    correlated = crdb_correlates.get("data", {}).get("correlated", [])

    story.append(heading(
        "演示：NPI 能力、VCS 与 CRDB 跨层检查",
        2,
        "kdebug-environment-crdb-demo",
    ))
    story.append(p(
        "批量分析前先检查三件事：当前 Verdi 中是否有需要的 Tcl NPI 命令，VCS/KDB 数据是否能由这个版本打开，"
        "以及 CRDB 等专用数据库能否正常读取。能看到命令并不代表许可证一定可用，因此 Power 功能还要执行真实查询。"
    ))
    story.extend(code_block("""KDEBUG=/home/host/kverif/tools/kdebug
DAIDIR=/home/host/kverif_npi_action_stress_20260729/fixture/design/simv.daidir
CRDB=/home/host/kverif_npi_action_stress_20260729/fixture/crdb/dut.crdb

$KDEBUG --json action npi.capabilities > /tmp/npi.capabilities.json

$KDEBUG --json action vcs.summary --daidir "$DAIDIR" \\
  > /tmp/vcs.summary.json

$KDEBUG --json action crdb.resolve \\
  --arg "crdb=$CRDB" --arg name=npi_crdb_top.state --arg level=RTL \\
  > /tmp/crdb.resolve.json

$KDEBUG --json action crdb.correlates \\
  --arg "crdb=$CRDB" --arg name=npi_crdb_top.state --arg level=RTL \\
  --limit max_rows=100 > /tmp/crdb.correlates.json""", "环境与数据库检查命令", max_lines=30))
    environment_rows = [
        (mono("npi.capabilities"),
         f"domains={capabilities.get('summary', {}).get('domain_count')}",
         f"available={capabilities.get('summary', {}).get('available_domain_count')}",
         "12 个 Tcl NPI 功能域的命令都存在"),
        (mono("vcs.summary"),
         mono(vcs_data.get("tool", {}).get("version", "")),
         f"modules={vcs_data.get('design', {}).get('modules')}",
         f"errors={vcs_data.get('compilation', {}).get('errors')} warnings={vcs_data.get('compilation', {}).get('warnings')}"),
        (mono("crdb.resolve"),
         mono(crdb_object.get("full_name", "")),
         f"level={crdb_object.get('level')}",
         f"type={crdb_object.get('type')} size={crdb_object.get('size')}"),
        (mono("crdb.correlates"),
         f"count={len(correlated)}",
         mono(correlated[0].get("full_name", "") if correlated else ""),
         f"target_level={correlated[0].get('level') if correlated else ''}"),
    ]
    story.append(data_table(["操作", "关键值", "核对值", "结果说明"], environment_rows,
                            [39 * mm, 52 * mm, 38 * mm, CONTENT_W - 129 * mm], small=True))
    story.append(callout(
        "不要把查询条件 level 和对象属性 level 当成同一个值",
        f"本例使用 {mono('level=RTL')} 作为查询条件；查到的对象自身 level 为 {mono('1')}，关联对象的 level 为 "
        f"{mono('2')}。脚本应分别保存查询条件、对象 level 和 full_name，不能只比较名称。",
        "info",
    ))
    story.append(p(
        "详细字段见 <link href=\"#action-npi.capabilities\">npi.capabilities</link>、"
        "<link href=\"#action-vcs.summary\">vcs.summary</link>、"
        "<link href=\"#action-crdb.resolve\">crdb.resolve</link> 和 "
        "<link href=\"#action-crdb.correlates\">crdb.correlates</link>。"
    ))
    story.append(callout(
        "VM 实测结果",
        "npi.capabilities、vcs.summary、crdb.resolve、crdb.correlates 四项均为 10/10 PASS；VCS 版本为 O-2018.09-SP2。",
        "note",
    ))


def make_writer_power_demo(story: list[Any]) -> None:
    transaction_response = npi_vm_response("transaction.writer.create")
    fsdb_response = npi_vm_response("fsdb.writer.create_scope")
    power_resolve = npi_vm_response("power.resolve")
    power_list = npi_vm_response("power.list")
    transaction_data = transaction_response.get("data", {})
    fsdb_data = fsdb_response.get("data", {})

    story.append(heading(
        "演示：创建 Transaction/FSDB 并检查 Power 许可证",
        2,
        "kdebug-writer-power-demo",
    ))
    story.append(p(
        "transaction.writer.create 和 fsdb.writer.create_scope 会根据输入数据创建新的 FSDB；"
        "power.resolve 和 power.list 会加载设计与 UPF，再查询电源对象。新 FSDB 写出后要重新打开确认；"
        "Power 查询失败时，则要先分清是输入有误还是许可证不可用。"
    ))
    transaction_request = {
        "args": {
            "output": "/tmp/kverif-npi-demo/transactions.fsdb",
            "overwrite": False,
            "unit": "1ns",
            "begin_time": 0,
            "stream": "bus.requests",
            "transactions": [
                {"start_delta": 10, "duration": 20, "type": "npiFsdbwTransTransaction", "label": "req0", "tags": ["read"]},
                {"start_delta": 5, "duration": 10, "type": "npiFsdbwTransTransaction", "label": "rsp0"},
            ],
            "relations": [{"relation": "npiFsdbwRelParentChild", "master": 0, "slave": 1}],
        }
    }
    fsdb_request = {
        "args": {
            "output": "/tmp/kverif-npi-demo/hierarchy.fsdb",
            "overwrite": False,
            "unit": "1ns",
            "begin_time": 0,
            "end_time_delta": 100,
            "operations": [
                {"op": "scope", "type": "npiFsdbScopeSvModule", "name": "top"},
                {"op": "scope", "type": "npiFsdbScopeSvModule", "name": "u_a"},
                {"op": "up"},
                {"op": "scope", "type": "npiFsdbScopeSvModule", "name": "u_b"},
            ],
        }
    }
    story.append(heading("创建事务 FSDB", 3, "writer-demo-transaction", toc=False, outline=True))
    story.extend(code_block(action_cli_example("transaction.writer.create", transaction_request), "绝对路径命令", max_lines=32))
    story.extend(code_block(json.dumps({
        "ok": transaction_response.get("ok"),
        "output": "/tmp/kverif-npi-demo/transactions.fsdb",
        "stream": transaction_data.get("stream"),
        "transaction_count": transaction_data.get("transaction_count"),
        "relation_count": transaction_data.get("relation_count"),
        "end_time": transaction_data.get("end_time"),
    }, ensure_ascii=False, indent=2), "VM 实测结果"))

    story.append(heading("创建层次 FSDB，并重新打开检查", 3, "writer-demo-hierarchy", toc=False, outline=True))
    story.extend(code_block(action_cli_example("fsdb.writer.create_scope", fsdb_request), "绝对路径命令", max_lines=32))
    story.extend(code_block("""/home/host/kverif/tools/kdebug --json action scope.list \\
  --fsdb /tmp/kverif-npi-demo/hierarchy.fsdb \\
  --path top --limit max_rows=100 > /tmp/kverif-npi-demo/reopen.json""", "重新打开并列出层次"))
    story.extend(code_block(json.dumps({
        "ok": fsdb_response.get("ok"),
        "output": "/tmp/kverif-npi-demo/hierarchy.fsdb",
        "scope_count": fsdb_data.get("scope_count"),
        "up_count": fsdb_data.get("up_count"),
        "reopen_scope_list": "PASS 10/10",
    }, ensure_ascii=False, indent=2), "VM 实测结果"))

    story.append(CondPageBreak(70 * mm))
    story.append(heading("检查 Power 功能的许可证", 3, "writer-demo-power", toc=False, outline=True))
    story.extend(code_block("""KDEBUG=/home/host/kverif/tools/kdebug
POWER=/home/host/kverif_npi_action_stress_20260729/fixture/power

$KDEBUG --json action power.resolve \\
  --target "filelist=$POWER/run.f" \\
  --target "upf=$POWER/demo.upf" \\
  --target "workdir=$POWER" \\
  --target 'defines=["NOVAS_UPF_PKG"]' \\
  --arg name=system/PD_TOP --arg object_type=npiPwPowerDomain \\
  > /tmp/power.resolve.json""", "命令"))
    power_error = power_resolve.get("error", {})
    story.extend(code_block(json.dumps({
        "ok": power_resolve.get("ok"),
        "action": power_resolve.get("action"),
        "error": {
            "code": power_error.get("code"),
            "message": power_error.get("message"),
            "recoverable": power_error.get("recoverable"),
            "feature": power_error.get("details", {}).get("feature"),
        },
    }, ensure_ascii=False, indent=2), "VM 实测结果"))
    story.append(callout(
        "看到 available 仍不能断定许可证可用",
        f"{mono('npi.capabilities')} 只能证明 Power Tcl 命令存在；本 VM 的 {mono('power.resolve')} 和 "
        f"{mono('power.list')} 各执行 10 次，均因缺少 {mono('PowerAwareAnalysis')} 返回 "
        f"{mono('LICENSE_UNAVAILABLE, recoverable=true')}。脚本应把它记录为环境阻塞，不能写成 PASS，也不能归因于 RTL。",
        "warn",
    ))
    story.append(p(
        "详细字段见 <link href=\"#action-transaction.writer.create\">transaction.writer.create</link>、"
        "<link href=\"#action-fsdb.writer.create_scope\">fsdb.writer.create_scope</link>、"
        "<link href=\"#action-power.resolve\">power.resolve</link> 和 "
        "<link href=\"#action-power.list\">power.list</link>。"
    ))
    story.append(callout(
        "VM 实测结果",
        "transaction writer 10/10 PASS；hierarchy FSDB writer 10/10 PASS 且重开 10/10 PASS；"
        f"Power 两项共 {sum(1 for item in (power_resolve, power_list) if item.get('error', {}).get('code') == 'LICENSE_UNAVAILABLE') * 10} 次许可阻塞。",
        "note",
    ))


def run_module(module: str, pythonpath: list[Path], args: list[str], cwd: Path | None = None) -> str:
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(str(path) for path in pythonpath + [ROOT])
    proc = subprocess.run(
        [sys.executable, "-m", module] + args,
        cwd=str(cwd or ROOT), env=env, text=True, capture_output=True,
        encoding="utf-8", errors="replace", timeout=30,
    )
    text = proc.stdout.strip() or proc.stderr.strip()
    if not text:
        return f"exit_code={proc.returncode}"
    try:
        parsed = json.loads(text)
        text = json.dumps(compact_value(parsed), ensure_ascii=False, indent=2)
    except Exception:
        pass
    return text


def sanitize_output(text: str) -> str:
    text = text.replace("\\\\", "\\")
    replacements = [
        (str(TMP_DIR / "kloc_fixture"), "/proj/tb"),
        (str(TMP_DIR), "/proj/out/manual_example"),
        (str(ROOT), "/home/host/kverif"),
        ("\\", "/"),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def kcov_example_output(action: str) -> str:
    samples: dict[str, dict[str, Any]] = {
        "actions": {"action_count": 22, "categories": ["session", "scope", "coverage", "export"]},
        "schema": {"schema_action": "cov.holes", "kind": "request", "required": ["api_version", "action"]},
        "session.open": {"session_id": "nightly", "vdb": "/proj/out/simv.vdb", "backend": "tcl_npi"},
        "session.status": {"session_id": "nightly", "ready": True, "test_count": 1},
        "session.close": {"session_id": "nightly", "closed": True},
        "tests.list": {"matched_count": 1, "returned": 1, "tests": ["merged"]},
        "metrics.list": {"matched_count": 5, "metrics": ["line", "toggle", "branch", "condition", "functional"]},
        "scope.summary": {"matched_count": 1, "scope": "top.u_dut", "covered": 73, "coverable": 100},
        "scope.search": {"matched_count": 1, "returned": 1, "full_name": "top.u_dut.u_fifo"},
        "cov.summary": {"line_pct": 92.5, "toggle_pct": 77.3, "branch_pct": 84.0},
        "cov.holes": {"matched_count": 3, "returned": 3, "first_hole": "top.u_dut.u_fifo.credit[0] 0 -> 1"},
        "cov.object.search": {"matched_count": 1, "full_name": "top.u_dut.u_fifo.credit"},
        "functional.summary": {"covergroup_pct": 88.0, "coverpoint_pct": 84.5},
        "functional.holes": {"matched_count": 2, "first_bin": "uart_cp.parity_err"},
        "export.summary": {"matched_count": 5, "output_mode": "summary_only"},
        "export.holes": {"output_path": ".kverif/kcov_exports/branch_holes.json", "written": 3},
        "export.scope_tree": {"output_path": ".kverif/kcov_exports/scope_tree.json", "scope_count": 4},
        "export.functional": {"output_path": ".kverif/kcov_exports/func_holes.csv", "written": 2},
        "scope.children": {"matched_count": 2, "children": ["top.u_dut.u_fifo", "top.u_dut.u_ctrl"]},
        "cov.object.get": {"full_name": "top.u_dut", "coverable": 100, "child_count": 2},
        "source.map": {"file": "rtl/ctrl.sv", "line": 88, "matched_count": 1, "object": "top.u_dut.u_ctrl.branch_7"},
    }
    payload = {
        "api_version": "kcov.v1", "ok": True, "action": action,
        "summary": samples.get(action, {"matched_count": 1, "returned": 1}),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def command_reference(story: list[Any], tool: str, command: str, purpose: str,
                      syntax: str, params: list[tuple[str, str, str]],
                      example: str, output: str, anchor_prefix: str,
                      note: str | None = None) -> None:
    anchor = f"cmd-{anchor_prefix}-{slug(command)}"
    story.append(CondPageBreak(68 * mm))
    story.append(heading(mono(f"{tool} {command}"), 3, anchor, toc=False, outline=True))
    story.append(p(esc(purpose)))
    story.extend(code_block(syntax, "命令格式", max_lines=8))
    if params:
        story.append(data_table(
            ["参数", "要求/默认", "说明"],
            [(mono(flag), esc(req), esc(desc)) for flag, req, desc in params],
            [47 * mm, 28 * mm, CONTENT_W - 75 * mm], small=True,
        ))
        story.append(Spacer(1, 4))
    story.extend(code_block(example, "完整命令示例", max_lines=14))
    story.extend(code_block(output, "运行后会看到", max_lines=24))
    if note:
        story.append(callout("结果怎么看", note, "info"))
    story.append(Spacer(1, 5))


def make_kbit_sections(story: list[Any]) -> None:
    story.append(heading("KBit：位宽和位运算", 1, "kbit-reference"))
    story.append(p(
        "KBit 专门处理位宽、符号和位运算，不读取 RTL、FSDB，也不调用 NPI。"
        "例如，KDebug 查到一个寄存器值后，可以交给 KBit 做切片、符号扩展或条件判断。"
        "这样 Bash、Perl 等脚本不用自己解析 8'hff 这类 SystemVerilog 数值。"
    ))
    story.append(heading("全部参数", 2, "kbit-all-params"))
    story.append(data_table(["参数", "适用范围/默认", "含义"],
                            [(mono(a), esc(b), esc(c)) for a, b, c in KBIT_PARAM_ROWS],
                            [43 * mm, 38 * mm, CONTENT_W - 81 * mm]))
    for name, purpose, args in KBIT_COMMANDS:
        if name == "agent serve":
            output = '{"id":1,"ok":true,"result":{"op":"eval","result":{"bool":true}}}'
            params = [("--stdio", "必填", "从标准输入逐行读取 JSON，并把结果逐行写到标准输出")]
            command_args = "agent serve --stdio"
        else:
            output = sanitize_output(run_module("kbit.cli", [ROOT / "kbit" / "src"], [name] + args))
            params = []
            command_args = " ".join([name] + [shell_value(arg) for arg in args])
        command_reference(
            story, "kbit", name, purpose,
            f"/home/host/kverif/tools/kbit {name} [options]",
            params,
            f"/home/host/kverif/tools/kbit {command_args}",
            output, "kbit",
            "退出码为 0 且 ok=true 才表示计算成功。成功后从 result 读取计算值；失败时读取 error.code。",
        )


def make_kentry_sections(story: list[Any]) -> None:
    story.append(heading("KEntry：拼接并拆解多拍数据", 1, "kentry-reference"))
    story.append(p(
        "KEntry 用来处理一个字段分散在多个时钟拍中的情况。YAML 文件说明每个字段占哪些位，JSONL 文件保存"
        "每一拍采到的数据片段。KEntry 会先拼成完整数据，再返回各字段的原始值，以及每个字段来自哪些片段。"
        "它不会直接读取 FSDB，也不会猜测协议含义；采集波形并生成 fragments 的工作由调用脚本负责。"
    ))
    story.append(heading("全部参数", 2, "kentry-all-params"))
    rows = [
        (mono("--config FILE"), "decode/explain/validate 必填", "YAML 字段布局。"),
        (mono("--input FILE"), "decode 必填，validate 可选", "JSONL 格式的逐拍数据片段。"),
        (mono("--json"), "false", "输出 JSON。"),
        (mono("--pretty"), "false", "缩进 JSON。"),
        (mono("- / request.json / '{...}'"), "JSON 兼容入口", "从 stdin、文件或字面量读取完整 request。"),
    ]
    story.append(data_table(["参数", "要求/默认", "含义"], rows,
                            [48 * mm, 43 * mm, CONTENT_W - 91 * mm]))
    local_config = str(ROOT / "kentry" / "examples" / "entry.yaml")
    local_input = str(ROOT / "kentry" / "examples" / "fragments.jsonl")
    for name, purpose, tail in KENTRY_COMMANDS:
        args = [name, "--config", local_config, "--json"]
        if name in {"decode", "validate"}:
            args += ["--input", local_input]
        output = sanitize_output(run_module("kentry.cli", [ROOT / "kentry" / "src"], args))
        params = [("--config", "必填", "字段布局 YAML 文件"), ("--json", "建议", "让脚本读取 JSON 结果")]
        if name in {"decode", "validate"}:
            params.insert(1, ("--input", "decode 必填", "逐拍数据片段 JSONL 文件"))
        command_reference(
            story, "kentry", name, purpose,
            f"/home/host/kverif/tools/kentry {name} [--config FILE] [--input FILE] [--json] [--pretty]",
            params,
            f"/home/host/kverif/tools/kentry {name} {tail}",
            output, "kentry",
            "decode 成功后，从 fields.*.raw_hex 或 raw_bin 读取字段值，从 source 查看字段来自哪些片段。errors 非空时不要继续给出成功结论。",
        )


def prepare_kloc_fixture() -> tuple[Path, Path, Path]:
    fixture = TMP_DIR / "kloc_fixture"
    fixture.mkdir(parents=True, exist_ok=True)
    source = fixture / "scoreboard.sv"
    source.write_text(
        "class scoreboard;\n  function void check();\n    `uvm_error(\"PKT_MISMATCH\", \"packet mismatch\")\n  endfunction\nendclass\n",
        encoding="utf-8",
    )
    mapping = fixture / "sim.log.kloc.jsonl"
    mapping.write_text(json.dumps({
        "loc_id": "L_00000001", "file": str(source), "line": 3, "msg_id": "PKT_MISMATCH"
    }) + "\n", encoding="utf-8")
    log = fixture / "sim.log"
    log.write_text(
        "UVM_ERROR L_00000001 @ 100ns: packet mismatch\n"
        "UVM_ERROR L_00000001 @ 120ns: packet mismatch\n",
        encoding="utf-8",
    )
    return source, mapping, log


def make_kloc_sections(story: list[Any]) -> None:
    story.append(heading("KLoc：从日志编号找到源码", 1, "kloc-reference"))
    story.append(p(
        "KLoc 把仿真日志中的短编号 loc_id 还原成源码文件和行号。它还能显示目标行前后的源码、"
        "统计哪些位置重复报错，并在原日志旁补上源码位置。KLoc 只依赖 Python 标准库。"
    ))
    story.append(heading("全部参数", 2, "kloc-all-params"))
    rows = [
        (mono("loc_id"), "resolve/context 必填", "例如 L_00000001。"),
        (mono("log"), "stats/annotate 必填", "仿真日志路径。"),
        (mono("--map FILE"), "resolve/context 必填", "loc_id 与源码位置的 JSONL 对照表；stats/annotate 可自动查找。"),
        (mono("--before N / --after N"), "20", "目标行前后各显示多少行源码。"),
        (mono("--top N"), "20", "最多列出多少个高频报错位置。"),
        (mono("--json"), "false", "resolve/context/stats 输出 JSON。"),
    ]
    story.append(data_table(["参数", "要求/默认", "含义"], rows,
                            [48 * mm, 43 * mm, CONTENT_W - 91 * mm]))
    _, mapping, log = prepare_kloc_fixture()
    for name, purpose, tail in KLOC_COMMANDS:
        if name in {"resolve", "context"}:
            args = [name, "L_00000001", "--map", str(mapping)]
            if name == "context":
                args += ["--before", "1", "--after", "1"]
            args += ["--json"]
        else:
            args = [name, str(log), "--map", str(mapping)]
            if name == "stats":
                args += ["--top", "10", "--json"]
        output = sanitize_output(run_module("kloc", [ROOT / "kloc"], args))
        command_reference(
            story, "kloc", name, purpose,
            f"/home/host/kverif/tools/kloc {name} [options]",
            [], f"/home/host/kverif/tools/kloc {name} {tail}", output, "kloc",
            "resolve 或 context 失败时不要猜源码位置。先检查 --map 文件是否正确，再确认 loc_id 是否存在。",
        )


def make_ksva_sections(story: list[Any]) -> None:
    story.append(heading("KSVA：读懂和检查断言", 1, "ksva-reference"))
    story.append(p(
        "KSVA 用来阅读和检查 SVA 断言。它既能生成一段通俗说明，也能把断言拆成 Surface IR、Sequence IR、"
        "Timeline IR 三种结构化结果，供脚本继续分析。KSVA 不运行仿真，只处理断言源码。"
    ))
    story.append(heading("全部参数", 2, "ksva-all-params"))
    rows = [
        (mono("--file FILE"), "全部命令必填", "SVA/SystemVerilog 文件。"),
        (mono("--property NAME"), "lint 可选；explain/parse 必填", "目标 property。"),
        (mono("--json"), "explain 可选", "输出解释 JSON。"),
        (mono("--markdown"), "explain 可选", "输出 Markdown。"),
        (mono("--strict"), "false", "遇到暂不支持的语法时立即报错退出。"),
        (mono("--emit LEVEL"), "parse 必填", "选择输出 surface-ir、sequence-ir 或 timeline-ir。"),
    ]
    story.append(data_table(["参数", "要求/默认", "含义"], rows,
                            [48 * mm, 47 * mm, CONTENT_W - 95 * mm]))
    local_file = ROOT / "ksva" / "tests" / "golden_ir" / "test_input.sva"
    for name, purpose, tail in KSVA_COMMANDS:
        args = [name, "--file", str(local_file)]
        if name in {"lint", "explain", "parse"}:
            args += ["--property", "p_req_ack"]
        if name == "explain":
            args += ["--json", "--strict"]
        if name == "parse":
            args += ["--emit", "timeline-ir"]
        output = sanitize_output(run_module("ksva", [ROOT / "ksva"], args))
        command_reference(
            story, "ksva", name, purpose,
            f"/home/host/kverif/tools/ksva {name} [options]",
            [], f"/home/host/kverif/tools/ksva {name} {tail}", output, "ksva",
            "CI 中建议使用 --strict，让不支持的语法直接失败。写给人看的报告用 explain；脚本继续分析时用 parse 返回的 IR JSON。",
        )


def make_kcov_sections(story: list[Any]) -> None:
    story.append(heading("KCov：查询和推进覆盖率", 1, "kcov-reference"))
    story.append(p(
        "KCov 通过 Verdi Tcl NPI 读取 VDB。只查一次时，可以在命令中直接写 --vdb；需要反复查询同一个 VDB 时，"
        "先用 open 打开会话，再执行多次查询会更省时间。为避免大型 VDB 被误判超时，Tcl 调用、会话启动和查询默认不设时限。"
    ))
    story.append(callout(
        "关于无限等待",
        f"{mono('KVERIF_KCOV_TCL_TIMEOUT_SEC=0')}、{mono('KVERIF_KCOV_STARTUP_TIMEOUT_SEC=0')} 和 "
        f"{mono('KVERIF_KCOV_REQUEST_TIMEOUT_SEC=0')} 都表示一直等待。关闭会话和清理进程仍有有限等待时间，避免留下后台进程。",
        "warn",
    ))
    story.append(heading("公共查询参数", 2, "kcov-common-options"))
    story.append(data_table(["参数", "值", "含义"],
                            [(mono(a), esc(b), esc(c)) for a, b, c in KCOV_COMMON_OPTIONS],
                            [47 * mm, 43 * mm, CONTENT_W - 90 * mm], small=True))
    story.append(heading("全部命令", 2, "kcov-all-commands"))
    index = []
    for spec in KCOV_COMMANDS:
        link = Paragraph(f'<link href="#cmd-kcov-{slug(spec["name"])}">{mono(spec["name"])}</link>', STYLES["TableCell"])
        index.append((link, esc(spec["action"]), esc(spec["purpose"])))
    story.append(data_table(["命令", "对应操作", "用途"], index,
                            [38 * mm, 42 * mm, CONTENT_W - 80 * mm]))
    for spec in KCOV_COMMANDS:
        specific = spec["specific"]
        command_reference(
            story, "kcov", spec["name"], spec["purpose"],
            f"{KCOV_BIN} {spec['name']} [common-options] [command-options]",
            specific,
            f"{KCOV_BIN} {spec['name']} {spec['tail']}",
            kcov_example_output(spec["action"]), "kcov",
            "这里的数值只用来说明字段。实际 covered、coverable、missing 和 matched_count 取决于你查询的 VDB。",
        )


def make_kberif_sections(story: list[Any]) -> None:
    story.append(heading("KBerif：保存和查询验证环境知识", 1, "kberif-reference"))
    story.append(p(
        "KBerif 用来保存和查询验证环境知识。每个主题有一份简短摘要，需要时还可以展开详细说明。"
        "命令默认输出便于人阅读的 KOUT；脚本需要 JSON 时，把全局参数 "
        f"{mono('--json')} 放在子命令前，例如 {mono('kberif --json status')}。"
    ))
    story.append(heading("公共与命令参数", 2, "kberif-all-params"))
    rows = [
        (mono("--json"), "全局，false", "查询命令输出 JSON；放在子命令前。"),
        (mono("--kind bt|it|st|soc"), "config init 必填", "环境类型。"),
        (mono("--force / --merge"), "false", "覆盖或合并已有配置。"),
        (mono("--dry-run"), "false", "只展示要写入的文件。"),
        (mono("--output DIR"), "当前目录", "配置输出项目根目录。"),
        (mono("--model NAME"), "init 必填", "首次生成知识条目时调用的模型名；配置文件不会保存密钥。"),
        (mono("--all"), "validate 可选", "校验全部状态。"),
        (mono("topic / card_id"), "命令相关", "主题名或知识条目 ID。"),
        (mono("--detail"), "false", "让 get 直接返回详细说明。"),
        (mono("--mode MODE"), "brief 必填", "指定使用场景，例如 debug。"),
        (mono("--stdin"), "写命令必填", "从标准输入读取 JSON 或 Markdown。"),
        (mono("--stdio"), "agent serve 必填", "通过标准输入/输出逐行收发 JSON。"),
        (mono("--write"), "false", "允许 agent 修改知识库。"),
    ]
    story.append(data_table(["参数", "要求/默认", "含义"], rows,
                            [49 * mm, 42 * mm, CONTENT_W - 91 * mm]))
    for command, purpose, tail, output in KBERIF_COMMANDS:
        example = f"cd /proj/nic && /home/host/kverif/tools/kberif {command} {tail}".rstrip()
        command_reference(
            story, "kberif", command, purpose,
            f"/home/host/kverif/tools/kberif [--json] {command} [options]",
            [], example, output, "kberif",
            "请通过 KBerif 命令维护 .kberif 目录。业务脚本不要直接修改 cards.json 或详细说明索引。",
        )


def make_keda_sections(story: list[Any]) -> None:
    story.append(heading("KEDA Runner：按批准清单运行 EDA 命令", 1, "keda-reference"))
    story.append(p(
        "KEDA Runner 只允许运行配置文件中明确批准的 EDA 命令和参数。init 会保存当前 EDA 环境，run 会在前台等待"
        "命令执行结束并返回相同退出码。长任务请放在 tmux、nohup 或调度系统中运行，避免终端断开后任务被终止。"
    ))
    story.append(heading("全部参数", 2, "keda-all-params"))
    rows = [
        (mono("--config FILE"), ".keda-runner.yaml", "配置文件，可放在主命令前。"),
        (mono("--refresh"), "false", "让 init 重新读取并保存当前环境。"),
        (mono("--action NAME"), "describe/run 必填", "配置中批准的操作名。"),
        (mono("--target NAME"), "由操作定义决定", "该操作允许使用的目标，例如 compile 或 run。"),
        (mono("--option KEY=VALUE"), "可重复", "给操作传参数；可选值和格式受配置文件限制。"),
        (mono("--quiet"), "false", "不打印 KEDA Runner 的开头信息。"),
        (mono("--dry-run"), "false", "只检查并打印最终命令，不真正执行，也不要求先运行 init。"),
    ]
    story.append(data_table(["参数", "要求/默认", "含义"], rows,
                            [49 * mm, 43 * mm, CONTENT_W - 92 * mm]))
    outputs = {
        "init": "[keda-runner] snapshot: /home/host/.keda_runner/env.snapshot\n[keda-runner] checks: vcs=/home/synopsys/vcs/bin/vcs\n[keda-runner] status=ready",
        "env-info": "shell: tcsh\nworkdir: /proj/nic/work\nsnapshot: ready\nchecks.vcs: /home/synopsys/vcs/bin/vcs",
        "list-actions": "sim\nregression\ncoverage",
        "describe-action": "action: sim\ncommand: make\nfixed_args: [-j8]\ntargets: [compile, run]\noptions: [TEST, SEED]",
        "run": "[keda-runner] runner_pid=543212 child_pid=543213\n[keda-runner] action=sim target=compile\n[keda-runner] command: make -j8 compile TEST=smoke SEED=123\n[keda-runner] exit_code=0",
    }
    for command, purpose, tail, _ in KEDA_COMMANDS:
        command_reference(
            story, "keda-runner", command, purpose,
            f"/home/host/kverif/tools/keda-runner [--config FILE] {command} [options]",
            [], f"/home/host/kverif/tools/keda-runner {command} {tail}".rstrip(),
            outputs[command], "keda",
            "run 返回的退出码与实际 EDA 命令相同。监控脚本还可以读取 runner_pid、child_pid 和日志路径。",
        )


def make_loop_mcp_sections(story: list[Any]) -> None:
    story.append(heading("复用长会话：Loop、MCP 与 LSF", 1, "loop-mcp-reference"))
    story.append(p(
        "Loop 让 Bash、Perl、Python 等脚本通过普通命令复用 KDebug 或 KCov 会话，不需要安装或调用任何 SDK。"
        "本机通信使用 Unix socket。MCP 则是给 AI 客户端准备的可选入口；两种入口使用同一套会话和启动方式，"
        "都可以在本机直接运行，也可以提交到 LSF。"
    ))
    story.append(heading("启动 Loop 服务", 2, "loop-server-params"))
    story.append(data_table(["参数", "默认", "含义"], [
        (mono("--socket PATH"), mono("/tmp/kverif-loop-<uid>.sock"), "脚本与服务通信使用的 Unix socket 路径。"),
        (mono("--backend direct|lsf"), "环境变量或 direct", "direct 表示本机启动，lsf 表示提交到 LSF。"),
    ], [50 * mm, 48 * mm, CONTENT_W - 98 * mm]))
    story.extend(code_block(
        "KVERIF_LOOP_BACKEND=direct /home/host/kverif/tools/kverif-loop-server \\\n"
        "  --socket /tmp/kverif-loop-host.sock",
        "启动命令",
    ))
    story.extend(code_block("kverif_loop_server:\n  socket: /tmp/kverif-loop-host.sock\n  backend: direct\n  ready: true", "示例输出"))

    story.append(heading("Loop 客户端参数", 2, "loop-client-common"))
    story.append(data_table(["参数", "默认", "含义"], [
        (mono("--socket PATH"), "按 UID 生成", "与 Loop 服务相同的 socket 路径。"),
        (mono("--timeout-sec N"), "cov.* 无限，其他 30s", "等待返回结果的秒数；0 或负数表示一直等待。"),
        (mono("--pretty"), "false", "缩进 JSON-RPC 返回结果。"),
        (mono("--json OBJECT"), "无", "发送一条完整 JSON-RPC 请求；否则可从 stdin 读取 JSONL。"),
        (mono("--session ID"), "query/close 必填", "要查询或关闭的会话别名。"),
        (mono("--action NAME"), "query 必填", "要执行的 KDebug 或 KCov 操作。"),
        (mono("--output-format"), "kout", "选择 KOUT、JSON，或带 JSON-RPC 外层字段的 envelope。"),
        (mono("--arg key=value"), "可重复", "传给这项操作的功能参数。"),
        (mono("--limit key=value"), "可重复", "限制最多返回多少项或查多深。"),
        (mono("--output key=value"), "可重复", "设置结果格式和详细程度。"),
        (mono("--queue / --resource"), "无", "使用 LSF 时指定队列和资源。"),
    ], [50 * mm, 49 * mm, CONTENT_W - 99 * mm], small=True))
    for command, purpose, tail, method in LOOP_CLIENT_COMMANDS:
        output = json.dumps({"id": f"cli-{command}", "ok": True, "method": method,
                             "result": {"status": "ok"}}, ensure_ascii=False, indent=2)
        command_reference(
            story, "kverif-loop-client", command, purpose,
            f"/home/host/kverif/tools/kverif-loop-client [common-options] {command} [options]",
            [],
            f"/home/host/kverif/tools/kverif-loop-client --socket /tmp/kverif-loop-host.sock {command} {tail}".rstrip(),
            output, "loop",
            "同一个会话中的请求会依次执行，不同会话可以并行。覆盖率查询默认一直等待，直到返回结果。",
        )

    story.append(heading("给 AI 客户端使用的 MCP 入口", 2, "mcp-tool-catalog"))
    story.extend(code_block(
        "PYTHONPATH=/home/host/kverif/kverif_mcp/src:/home/host/kverif \\\n"
        "KVERIF_HOME=/home/host/kverif \\\n"
        "KVERIF_MCP_BACKEND=direct \\\n"
        "/home/host/kverif/tools/kverif-mcp",
        "启动命令",
    ))
    story.append(p(
        "MCP 不是普通脚本的必需项。Shell、Perl 和 Python 脚本直接运行 tools 目录中的命令即可；"
        "只有需要通过 MCP 协议调用工具的 AI 客户端才要使用这一入口。下表列出当前注册的 MCP 工具和参数。"
    ))
    tools = parse_mcp_tools()
    group_names = {
        "common": "通用",
        "debug": "设计/波形",
        "cov": "覆盖率",
        "bit": "位运算",
        "entry": "多拍数据",
        "loc": "日志定位",
        "context": "知识查询",
        "context_write": "知识维护",
        "sva": "断言",
    }
    rows = []
    for item in tools:
        rows.append((mono(item["name"]), esc(group_names.get(item["group"], item["group"])),
                     esc(item["signature"]), esc(item["summary"])))
    story.append(data_table(["MCP 工具", "所属组", "参数", "功能"], rows,
                            [39 * mm, 18 * mm, 65 * mm, CONTENT_W - 122 * mm], small=True))
    story.append(heading("LSF 自检", 2, "lsf-doctor"))
    story.extend(code_block("/home/host/kverif/tools/kverif-lsf-doctor", "命令"))
    story.extend(code_block(
        "kverif_lsf_doctor:\n  python_version: 3.11.9\n  mcp_sdk_import: ok\n  mode: direct\n"
        "  process_started: true\n  actions_ok: true\n  quit_ok: true",
        "示例输出",
    ))


MCP_TOOL_DESCRIPTIONS = {
    "kverif_ping": "检查 KVerif MCP 服务是否仍在运行。",
    "kverif_batch": "读取 NDJSON 批处理文件，按顺序执行其中的多项 MCP 工具请求。",
    "kverif_debug_list_actions": "列出 KDebug 当前支持的操作。",
    "kverif_debug_get_schema": "查看某项 KDebug 操作可以输入和返回哪些 JSON 字段。",
    "kverif_debug_raw_request": "直接执行一份完整的 KDebug JSON 请求，不打开可复用会话。",
    "kverif_debug_session_open": "打开可重复查询的 KDebug 设计或波形会话。",
    "kverif_debug_session_list": "列出由 MCP 服务管理的 KDebug 会话。",
    "kverif_debug_session_close": "关闭 KDebug 会话并释放后台进程。",
    "kverif_debug_query": "在已打开的 KDebug 会话中执行一项操作。",
    "kverif_cov_list_actions": "列出 KCov 当前支持的操作。",
    "kverif_cov_get_schema": "查看某项 KCov 操作可以输入和返回哪些 JSON 字段。",
    "kverif_cov_raw_request": "直接执行一份完整的 KCov JSON 请求，不打开可复用会话。",
    "kverif_cov_session_open": "打开可重复查询的覆盖率数据库会话。",
    "kverif_cov_session_list": "列出由 MCP 服务管理的 KCov 会话。",
    "kverif_cov_session_close": "关闭 KCov 会话并释放后台进程。",
    "kverif_cov_query": "在已打开的 KCov 会话中执行一项覆盖率查询。",
    "kverif_bit_convert": "解析 SystemVerilog 数值，并转换进制、位宽或符号属性。",
    "kverif_bit_eval": "计算一条位运算或常量表达式。",
    "kverif_bit_slice": "从一个数值中取出指定的连续位。",
    "kverif_bit_check": "代入变量值，判断位表达式是否成立。",
    "kverif_entry_decode": "按配置拼接多拍数据，并拆出各字段的原始值。",
    "kverif_entry_explain": "查看多拍数据配置中每个字段占哪些位。",
    "kverif_entry_validate": "检查多拍数据配置和输入片段格式是否正确。",
    "kverif_loc_resolve": "把日志中的 loc_id 还原成源码文件和行号。",
    "kverif_loc_context": "根据 loc_id 显示目标行前后的源码。",
    "kverif_loc_stats": "统计仿真日志中重复最多的 loc_id。",
    "kverif_loc_annotate": "在仿真日志旁补上对应的源码位置。",
    "kverif_context_status": "查看 KBerif 知识库中有哪些环境、主题和详细说明。",
    "kverif_context_topics": "列出 KBerif 中可以查询的主题。",
    "kverif_context_brief": "按指定工作场景整理一份精简的验证环境说明。",
    "kverif_context_topic": "读取一个主题的摘要，并可选择同时返回详细说明。",
    "kverif_context_topic_detail": "读取一个主题的完整 Markdown 说明。",
    "kverif_context_validate": "检查 KBerif 的主题摘要和详细说明是否一致。",
    "kverif_context_init_config": "创建 KBerif 环境类型配置；必须显式启用写权限。",
    "kverif_context_init_project": "初始化 KBerif 项目目录；必须显式启用写权限。",
    "kverif_context_repair_index": "根据已有知识条目重建 KBerif 目录；必须显式启用写权限。",
    "kverif_sva_list_properties": "列出 SVA 文件中的 property 和 assertion 名称。",
    "kverif_sva_scan_constructs": "统计 SVA 文件中使用了哪些语法结构。",
    "kverif_sva_parse_property": "把一条 SVA property 转成供程序继续处理的结构化数据。",
    "kverif_sva_explain_property": "用较容易阅读的文字解释一条 SVA property。",
    "kverif_tools": "列出当前 MCP 服务已经注册的 KVerif 工具。",
    "kverif_tool_help": "查看一个 KVerif MCP 工具的参数和详细说明。",
    "kverif_wave_value_at": "读取某个信号在指定波形时间的值。",
    "kverif_wave_changes": "列出信号在指定时间范围内的跳变。",
    "kverif_wave_generate_rc": "根据配置生成 Verdi RC 文件。",
    "kverif_design_trace_driver": "结合指定时刻的波形，查找当时真正生效的信号驱动。",
}


def parse_mcp_tools() -> list[dict[str, str]]:
    path = ROOT / "kverif_mcp" / "src" / "kverif_mcp" / "server.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    result = []
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        group = None
        for dec in node.decorator_list:
            if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Name) and dec.func.id == "kverif_tool":
                if dec.args and isinstance(dec.args[0], ast.Constant):
                    group = str(dec.args[0].value)
        if group is None:
            continue
        args = [arg.arg for arg in node.args.args]
        defaults = [None] * (len(args) - len(node.args.defaults)) + list(node.args.defaults)
        parts = []
        for name, default in zip(args, defaults):
            if default is None:
                parts.append(name)
            else:
                try:
                    parts.append(f"{name}={ast.unparse(default)}")
                except Exception:
                    parts.append(f"{name}=...")
        doc = ast.get_docstring(node) or ""
        summary = MCP_TOOL_DESCRIPTIONS.get(node.name)
        if summary is None:
            summary = doc.strip().splitlines()[0] if doc.strip() else "通过 MCP 调用 KVerif 命令。"
        result.append({"name": node.name, "group": group, "signature": ", ".join(parts), "summary": summary})
    return result


def make_secondary_development(story: list[Any]) -> None:
    story.append(heading("脚本怎样调用 KVerif", 1, "secondary-patterns"))
    story.append(p(
        "二次开发脚本只需要运行 tools 目录中的命令，然后检查退出码并读取标准输出中的 JSON。"
        "不需要导入 KVerif 的 Python 包，也不需要 source 内部 Tcl，更不要直接调用 NPI 函数。"
        "下面四个示例都会先运行工具，再读取结果并给出脚本自己的判断。"
    ))
    story.append(callout(
        "建议保存这些信息",
        "建议保存实际命令、工具返回的原始 JSON、脚本最后的判断、输入文件哈希和工具版本。"
        "只要出现 ok=false、truncated=true、error，或关键字段缺失，脚本就不应输出 PASS。",
        "warn",
    ))

    examples = [
        ("Bash: 检查波形是否正常", """#!/usr/bin/env bash
set -euo pipefail
KDEBUG=/home/host/kverif/tools/kdebug
OUT=/proj/out/health; mkdir -p "$OUT"
"$KDEBUG" --json action signal.scan \\
  --fsdb /proj/out/waves.fsdb \\
  --arg signal=top.u_dut.ready --arg begin=0ns --arg end=1us \\
  --max-rows 500 > "$OUT/tool.json"
python3 - "$OUT/tool.json" "$OUT/conclusion.json" <<'PY'
import json, sys
r=json.load(open(sys.argv[1])); s=r.get("summary", {})
ok=r.get("ok") is True and not s.get("truncated")
status="HEALTHY" if ok and s.get("change_count",0)>0 and s.get("unknown_count",0)==0 else "REVIEW"
json.dump({"status":status,"evidence":s},open(sys.argv[2],"w"),sort_keys=True)
raise SystemExit(0 if status=="HEALTHY" else 3)
PY""", "status=HEALTHY; evidence.change_count=14; evidence.unknown_count=0"),
        ("csh: 判断是否还有未覆盖项", """#!/bin/csh -f
set KCOV=/home/host/kverif/tools/kcov
set OUT=/proj/out/cov_holes.json
$KCOV cov-holes --vdb /proj/out/simv.vdb --metrics branch \\
  --max-items 200 --json >! $OUT
python3 -c 'import json,sys; r=json.load(open(sys.argv[1])); \
n=r["summary"].get("matched_count",0); print("CLOSED" if n==0 else "OPEN:%d"%n); \
sys.exit(0 if n==0 else 3)' $OUT
exit $status""", "OPEN:7\nexit_code=3"),
        ("Perl: 多时刻批量采样", """#!/usr/bin/env perl
use strict; use warnings; use JSON::PP qw(decode_json encode_json);
my $k='/home/host/kverif/tools/kdebug';
my @cmd=($k,'--json','value-batch','--fsdb','/proj/out/waves.fsdb',
  '--signal','top.req','--signal','top.ack','--time','100ns');
open my $fh, '-|', @cmd or die $!; local $/; my $raw=<$fh>; close $fh;
my $r=decode_json($raw); die encode_json($r->{error}) unless $r->{ok};
my $v=$r->{data}{values};
my $status=($v->{'top.req'} eq "1'b1" && $v->{'top.ack'} eq "1'b1")
  ? 'TRANSFER' : 'WAIT';
print encode_json({status=>$status,time=>'100ns',evidence=>$v}),"\n";""", '{"status":"TRANSFER","time":"100ns","evidence":{"top.req":"1\'b1","top.ack":"1\'b1"}}'),
        ("Python: 模块连接完整性", """#!/usr/bin/env python3
import json, subprocess
k='/home/host/kverif/tools/kdebug'
cmd=[k,'--json','action','module.inspect','--daidir','/proj/out/simv.daidir',
     '--arg','module=top.u_dut','--arg','sections=["ports","io","instances"]']
r=json.loads(subprocess.run(cmd,check=True,text=True,capture_output=True).stdout)
if not r.get('ok'): raise RuntimeError(r.get('error'))
ports=r['data']['sections']['ports']
unconnected=[x['object']['full_name'] for x in ports
             if not any(x.get('connections',{}).values())]
conclusion={'status':'PASS' if not unconnected else 'OPEN_PORTS',
            'module':'top.u_dut','unconnected':unconnected}
print(json.dumps(conclusion,sort_keys=True))
raise SystemExit(0 if not unconnected else 3)""", '{"module":"top.u_dut","status":"OPEN_PORTS","unconnected":["top.u_dut.debug_o"]}'),
    ]
    for index, (title, source, output) in enumerate(examples, 1):
        story.append(heading(title, 2, f"secondary-example-{index}"))
        story.extend(code_block(source, "脚本", max_lines=30))
        story.extend(code_block(output, "脚本得到的结果", max_lines=8))

    story.append(heading("几个常用的组合用法", 2, "secondary-recipes"))
    recipe_rows = [
        ("定位波形问题", "session.open -> signal.scan -> trace.active_driver_chain -> source.context", "第一次异常的时间、当时生效的驱动链和源码位置"),
        ("检查模块连线", "module.inspect -> module.objects(kind=instances/ports/parameters) -> trace.graph", "未连接端口、实例定义、实际参数值和依赖图"),
        ("推进覆盖率", "kcov open -> cov.holes -> source.map -> 回归 -> cov.summary -> close", "未覆盖项、对应源码，以及回归前后的覆盖率变化"),
        ("分析协议性能", "axi.query -> axi.channel_stall -> axi.latency_outlier -> axi.outstanding_timeline", "慢事务、发生阻塞的通道和未完成事务峰值"),
        ("从日志找到源码", "kloc stats -> kloc resolve/context -> kdebug source.context", "重复最多的报错位置和附近源码"),
        ("检查断言", "ksva scan/lint -> explain -> parse timeline-ir", "不支持的语法、断言要求的时序关系和结构化结果"),
    ]
    story.append(data_table(["要解决的问题", "操作顺序", "脚本最后得到什么"], recipe_rows,
                            [34 * mm, 84 * mm, CONTENT_W - 118 * mm]))


def make_security_testing(story: list[Any], stress: dict[str, Any]) -> None:
    story.append(heading("错误处理、安全与验证", 1, "operations"))
    story.append(heading("脚本怎样判断成功还是失败", 2, "exit-codes"))
    story.append(data_table(["检查位置", "成功时", "失败或不完整时", "脚本应该怎么做"], [
        ("命令退出码", mono("exit 0"), mono("exit 1/2/3"), "保存 stdout 和 stderr，停止后续成功判断。"),
        ("JSON 的 ok", mono("ok=true"), mono("ok=false + error.code"), "按 error.code 判断是重试、补输入，还是修正参数。"),
        ("结果完整性", mono("truncated=false"), mono("truncated=true"), "需要完整清单时提高数量上限，或改为导出文件。"),
        ("会话状态", mono("ready/healthy"), mono("SESSION_LOST"), "运行 session.doctor 检查；必要时重新打开会话。"),
        ("许可证", mono("feature available"), mono("LICENSE_UNAVAILABLE"), "记录为测试环境问题，不能据此写成功能通过。"),
    ], [31 * mm, 34 * mm, 43 * mm, CONTENT_W - 108 * mm]))

    story.append(heading("凭据与日志", 2, "security"))
    story.extend(bullets([
        "API key、许可证密钥和 token 只通过运行时环境传入，不写进请求、命令记录、报告或 Git。",
        "标准输出 stdout 只放程序结果；诊断信息写到 stderr，以及 ~/.kdebug、~/.kverif 下的日志文件。",
        "上传测试材料前检查命令、环境信息和进程信息，删除真实凭据和内部服务器地址。",
        "写操作必须指定独立的 output_dir 或 output_file；text.replace_line、dm.add_net、dm.clone_module 不得覆盖原始 RTL。",
        "KCov 绝对导出路径必须显式 --allow-absolute-path；含 .. 的相对路径应拒绝。",
    ]))

    story.append(heading("Verdi 2018 VM 验证结果", 2, "vm-validation"))
    totals = stress.get("totals", {})
    scope = stress.get("scope", {})
    env = stress.get("environment", {})
    rows = [
        ("执行用户", esc(env.get("user", "host")), "普通用户"),
        ("Verdi", esc(Path(str(env.get("verdi_home", "O-2018.09-SP2"))).name), "KDebug 通过它执行 Tcl NPI"),
        ("独立测试项", esc(scope.get("independent_cases", 36)), "其中 module.objects 按 15 种 kind 分别测试"),
        ("操作执行次数", esc(totals.get("attempts", 360)), "不包含重新打开生成文件的检查"),
        ("PASS", esc(totals.get("passed", 340)), "功能检查通过"),
        ("LICENSE_BLOCKED", esc(totals.get("license_blocked", 20)), "power.resolve/list 缺 PowerAwareAnalysis"),
        ("非预期失败", esc(totals.get("failed", 0)), "0"),
        ("命令行调用次数", esc(totals.get("public_cli_invocations", 370)), "测试只运行 tools 目录中的命令，没有直接调用 Tcl/NPI"),
    ]
    story.append(data_table(["指标", "结果", "解释"], rows,
                            [42 * mm, 42 * mm, CONTENT_W - 84 * mm]))
    command = stress.get("run", {}).get("command", "")
    if command:
        story.extend(code_block(str(command), "已执行压测命令", max_lines=10))
    story.append(callout(
        "Power 测试说明",
        "除 Power 外，20 项新增 NPI 操作都通过了 10 轮功能测试。Power 两项能够正常启动并准确报告许可证缺失，"
        "但这不能证明 Power 查询功能已经通过。获得 PowerAwareAnalysis 许可证后仍要重新测试。",
        "warn",
    ))


def make_appendices(story: list[Any], actions: list[dict[str, Any]]) -> None:
    story.append(heading("附录", 1, "appendices"))
    story.append(heading("环境变量速查", 2, "environment-index"))
    story.append(data_table(["变量", "含义"],
                            [(mono(name), esc(desc)) for name, desc in ENVIRONMENT_ROWS],
                            [65 * mm, CONTENT_W - 65 * mm], small=True))

    story.append(heading("常见状态和术语", 2, "glossary"))
    glossary = [
        ("design", "这项操作需要 simv.daidir、filelist，或已经加载设计的 session。"),
        ("waveform", "这项操作需要 FSDB，或已经加载波形的 session。"),
        ("combined/any", "combined 表示同时需要设计和波形；any 表示两者至少提供一种。"),
        ("stable", "这项操作已经稳定，自动测试会检查其主要行为不被意外改坏。"),
        ("experimental", "功能已经实现，但字段或行为以后仍可能调整。"),
        ("deprecated", "只为兼容旧脚本而保留，新脚本不要再使用。"),
        ("KOUT", "KVerif 默认使用的、便于人在终端阅读的结构化文本。"),
        ("标准示例", "仓库中与字段定义配套的请求和返回示例，只用于说明格式，不代表你的项目实测值。"),
        ("只调用命令行", "二次开发脚本只运行 tools 目录中的可执行文件，不直接调用内部 Tcl、NPI 或 Python 模块。"),
    ]
    story.append(data_table(["术语", "定义"], glossary, [45 * mm, CONTENT_W - 45 * mm]))

    story.append(heading("KDebug 操作字母索引", 2, "action-alpha-index"))
    rows = []
    for action in sorted(actions, key=lambda item: item["name"]):
        name = action["name"]
        rows.append((
            Paragraph(f'<link href="#action-{slug(name)}">{mono(name)}</link>', STYLES["TableCell"]),
            esc(action["category"]), esc(action["status"]), esc(action["requires"]),
            esc(ACTION_PURPOSE.get(name, "")),
        ))
    story.append(data_table(["操作名", "分类", "状态", "需要的输入", "用途"], rows,
                            [38 * mm, 19 * mm, 21 * mm, 21 * mm, CONTENT_W - 99 * mm], small=True))

    story.append(heading("本手册包含哪些内容", 2, "coverage-statement"))
    story.append(callout(
        "本版覆盖",
        f"{len(TOOL_MATRIX)} 类对外工具、{len(actions)} 项可用的 KDebug 操作、全部 KDebug 快捷命令和 key=value 通用参数；"
        f"22 条 KCov 命令，以及 KBit、KEntry、KLoc、KSVA、KBerif、KEDA Runner、Loop 客户端的命令；"
        f"{len(parse_mcp_tools())} 个 MCP 工具的参数；{len(WORKFLOW_COVERAGE)} 个按任务编排的 NPI 教程；"
        f"{len(NPI_WORKFLOW_ACTIONS)} 项 NPI 操作和 {len(MODULE_OBJECT_KINDS)} 类模块对象；"
        "以及 Bash、csh、Perl、Python 调用示例。",
        "note",
    ))
    story.append(p(
        "本手册根据当前仓库内容自动生成。修改操作字段或命令行解析逻辑后，应重新生成 PDF，并再次检查目录链接、"
        "内容是否齐全、文字是否越界，以及每一页能否正常显示。"
    ))


def make_beginner_quickstart(story: list[Any]) -> None:
    story.append(heading("第一次使用：10 分钟拿到真实结果", 1, "beginner-quickstart"))
    story.append(callout(
        "先跑通，再查参数",
        "第一次使用时，不需要先理解 action、target、args 或 NPI 对象。先运行环境检查和随库教程，"
        "看到 PASS 并找到 result.json、tool-response.json、replay.sh 后，再查询自己的项目。",
        "info",
    ))
    story.append(heading("先运行这三条命令", 2, "beginner-three-commands"))
    story.extend(code_block("""su - host
export KVERIF_HOME=/home/host/kverif
export PATH="$KVERIF_HOME/tools:$PATH"

/home/host/kverif/tools/kverif doctor
/home/host/kverif/tools/kverif tutorial waveform
/home/host/kverif/tools/kverif tasks""", "普通用户 host"))
    story.append(data_table(["命令", "它检查什么", "成功时看到什么"], [
        (mono("kverif doctor"), "用户、Python、KDebug、Verdi、Tcl NPI 和随库文件。", "最后是 PASS，required failures 为 0。"),
        (mono("kverif tutorial waveform"), "真实 Verdi 2018 FSDB 能否被读取和校验。", "变化 5 次、unknown 0、Tutorial checks: PASS。"),
        (mono("kverif tasks"), "当前提供哪些任务式入口。", "列出模块检查、波形检查、教程和脚手架。"),
    ], [46 * mm, 72 * mm, CONTENT_W - 118 * mm]))
    story.append(heading("每次任务会留下什么", 2, "beginner-artifacts"))
    story.append(data_table(["文件", "给谁看", "内容"], [
        (mono("result.json"), "验证人员和上层脚本", "整理后的结论和常用字段。"),
        (mono("tool-response.json"), "需要追查细节的人", "KDebug 返回的原始 JSON，保留底层事实。"),
        (mono("replay.sh"), "复现问题的人", "本次实际使用的底层命令，可直接重放。"),
        (mono("error.json"), "失败排查", "失败码、提示、相关诊断和产物路径。只在失败时生成。"),
    ], [42 * mm, 40 * mm, CONTENT_W - 82 * mm]))

    story.append(heading("第一次分析模块", 2, "beginner-module"))
    story.append(p(
        "模块查询需要 VCS 生成的 simv.daidir。它适合回答模块实例在哪里、parameter 展开后是多少、"
        "端口方向和连接是什么。FSDB 只有波形值，不能替代 simv.daidir 做这类设计查询。"
    ))
    story.extend(code_block("""# 先用随库的参数化模块完成教程
/home/host/kverif/tools/kverif doctor --require-vcs
/home/host/kverif/tools/kverif tutorial module-inspect \
  --out /home/host/kverif_tutorial

# 再查询自己的设计
/home/host/kverif/tools/kverif inspect-module \
  --input /data/project/build/simv.daidir \
  --module tb_top.dut.u_core.u_alu \
  --out /data/project/reports/alu-module""", "模块检查"))
    story.extend(code_block("""PASS  module inspection completed

Module path: npi_fixture_top.u_alu
Definition: npi_fixture_alu
Parameters: 3
  - WIDTH = 12
  - BIAS = 1
  - RESULT_WIDTH = 12 (localparam)
Ports: 3
  - input  lhs                  [12 bits]
  - input  rhs                  [12 bits]
  - output result               [12 bits]
Tutorial checks: PASS""", "教程期望输出"))
    story.append(callout(
        "module 要填完整实例路径",
        "例如 tb_top.dut.u_core.u_alu，而不是 RTL 中的 ALU 定义名。只想检查生成的命令时，"
        "增加 --dry-run --show-command，不会启动 Verdi。",
        "warn",
    ))

    story.append(heading("第一次分析波形", 2, "beginner-waveform"))
    story.extend(code_block("""/home/host/kverif/tools/kverif trace-signal \
  --input /data/project/run/waves.fsdb \
  --signal tb_top.dut.req_valid \
  --begin 0ns --end 2us \
  --format hex --max-rows 500 \
  --out /data/project/reports/req-valid""", "波形检查"))
    story.extend(code_block("""PASS  waveform inspection completed

Signal: tb_top.dut.req_valid
Window: 0ns .. 2us
Changes: 14
Unknown values: 0
Truncated: no""", "输出示例"))
    story.append(p(
        "终端只显示最常用的结论。脚本需要详细跳变时读取 tool-response.json；不要用 grep 从终端文字猜 JSON 字段。"
    ))

    story.append(heading("从可运行脚本开始二次开发", 2, "beginner-scaffold"))
    story.extend(code_block("""/home/host/kverif/tools/kverif new signal-check \
  --lang perl \
  --out /data/project/tools/check_req_valid

cd /data/project/tools/check_req_valid
KVERIF_HOME=/home/host/kverif bash ./example.sh""", "生成并运行"))
    story.append(data_table(["--lang", "生成入口", "怎样处理结果"], [
        (mono("sh"), mono("sh/signal_health.sh"), "调用 KDebug，再用独立 JSON helper 生成结论。"),
        (mono("csh"), mono("csh/signal_health.csh"), "适合传统 EDA 环境，仍只调用可执行文件。"),
        (mono("perl"), mono("perl/signal_health.pl"), "只使用 Perl 核心模块处理工具输出。"),
        (mono("python"), mono("py/signal_health.py"), "只使用 subprocess 和 json 标准库，不导入 KVerif。"),
    ], [25 * mm, 55 * mm, CONTENT_W - 80 * mm]))
    story.append(callout(
        "二次开发边界没有改变",
        "生成目录不包含 NPI Tcl、NPI C/C++ 头文件，也不导入 KVerif 内部模块。业务脚本只运行 tools 目录中的命令。",
        "note",
    ))


def build_story(actions: list[dict[str, Any]], tests: dict[str, str], stress: dict[str, Any]) -> list[Any]:
    story: list[Any] = []
    category_counts = Counter(item["category"] for item in actions)

    story.extend([
        Spacer(1, 29 * mm),
        p("KVERIF", "CoverMeta"),
        Spacer(1, 8 * mm),
        p("新手上手与二次开发手册", "CoverTitle"),
        p("先用三条命令跑通，再按任务查表", "CoverSub"),
        Spacer(1, 12 * mm),
        HRFlowable(width="68%", thickness=2, color=AMBER, hAlign="LEFT"),
        Spacer(1, 8 * mm),
        p(
            "面向芯片验证工程师、回归平台开发者与 AI 工具集成人员。<br/>"
            "按任务分类检索命令；每个命令提供参数、绝对路径示例和输出解释。",
            "CoverMeta",
        ),
        Spacer(1, 24 * mm),
    ])
    cover_stats = Table([
        [p(f"<b>{len(actions)}</b><br/>项 KDebug 操作", "CoverMeta"),
         p("<b>22</b><br/>条 KCov 命令", "CoverMeta"),
         p(f"<b>{len(TOOL_MATRIX)}</b><br/>类对外工具", "CoverMeta")],
    ], colWidths=[48 * mm] * 3)
    cover_stats.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), HexColor("#0A5960")),
        ("BOX", (0, 0), (-1, -1), 0.5, HexColor("#4E898E")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, HexColor("#4E898E")),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.extend([
        cover_stats,
        Spacer(1, 25 * mm),
        p(f"版本 {VERSION}<br/>发布日期 {PUBLICATION_DATE}<br/>兼容基线 Verdi O-2018.09-SP2 / 普通用户 host", "CoverMeta"),
        NextPageTemplate("body"),
        PageBreak(),
    ])

    story.append(heading("文档控制", 1, "document-control"))
    story.append(data_table(["项目", "内容"], [
        ("文档用途", "说明各工具能做什么、命令怎么写、参数怎么填、输出怎么看。"),
        ("推荐调用方式", "二次开发脚本只运行 tools 目录中的可执行文件，然后检查退出码并读取 JSON 输出。"),
        ("不包含", "内部 Tcl/NPI 函数调用、私有 SDK、真实凭据和许可证服务器信息。"),
        ("内容来源", "当前命令行实现、JSON 字段定义、仓库示例、README 和 VM 测试结果。"),
        ("验证基线", "普通用户 host，Verdi O-2018.09-SP2，VCS O-2018.09-1。"),
    ], [42 * mm, CONTENT_W - 42 * mm]))
    story.append(Spacer(1, 5))
    story.append(callout(
        "阅读方式",
        "PDF 目录、书签和操作索引都可以点击。参数表中的“必填”来自程序实际使用的 JSON 字段定义。"
        "标有“VM 实测”的输出来自测试机；标有“标准输出示例”的内容只用于说明字段，实际数值取决于你的设计、FSDB 或 VDB。",
        "info",
    ))
    story.append(heading("阅读前先认识这些词", 2, "plain-language-terms"))
    story.append(data_table(["手册中的写法", "通俗解释"], [
        (mono("action"), "操作名。它告诉 KDebug 要做什么，例如 module.inspect 表示查看模块。"),
        (mono("target"), "要读取的设计、波形或已打开会话，例如 daidir、FSDB 或 session_id。"),
        (mono("args"), "这项操作要用的具体参数，例如模块名、信号名和时间。"),
        (mono("summary"), "简要结果。脚本通常先读这里，快速判断数量、状态或是否找到对象。"),
        (mono("data"), "详细结果。需要逐个对象、逐笔事务或完整路径时读取这里。"),
        (mono("truncated"), "结果是否因为数量上限被截短。需要完整清单时必须确认它是 false。"),
        (mono("session"), "已经加载好设计或波形的后台进程。重复查询时不用每次重新打开大文件。"),
    ], [48 * mm, CONTENT_W - 48 * mm]))
    story.append(PageBreak())

    story.append(heading("目录", 1, "contents", toc=False))
    toc = TableOfContents()
    toc.levelStyles = [STYLES["TOC0"], STYLES["TOC1"]]
    toc.dotsMinLevel = 0
    story.extend([toc, PageBreakIfNotEmpty()])

    make_beginner_quickstart(story)

    story.append(heading("按任务选择工具", 1, "choose-tool"))
    story.append(p(
        "选工具时先看手里有什么文件，再看要解决什么问题。查设计或波形用 KDebug；查覆盖率用 KCov；"
        "位运算、日志定位和断言解释则分别使用后面的专用工具。"
    ))
    story.append(data_table(["工具", "任务域", "主要输入", "典型输出"], TOOL_MATRIX,
                            [27 * mm, 34 * mm, 47 * mm, CONTENT_W - 108 * mm]))
    story.append(Spacer(1, 7))
    story.append(architecture_drawing())
    story.append(heading("快速决策", 2, "quick-decision"))
    story.append(data_table(["问题", "首选命令", "下一步"], [
        ("某个时刻信号是什么值", mono("kdebug value-at"), "如果还要查为什么是这个值，再用 trace.active_driver。"),
        ("谁在驱动这个信号", mono("kdebug trace-driver"), "如果要结合波形判断当时哪条赋值真正生效，用 active-driver-chain。"),
        ("模块在哪里例化，参数是多少", mono("kdebug action module.inspect"), "需要分类列出端口或实例时，用 module.objects。"),
        ("哪些覆盖项还没命中", mono("kcov cov-holes"), "再用 source-map 找到对应源码，并比较回归前后的变化。"),
        ("计算位宽、符号或切片", mono("kbit eval"), "交给 KBit 计算，避免脚本自己处理符号扩展。"),
        ("日志中的 loc_id 对应哪行源码", mono("kloc resolve/context"), "先找高频位置时使用 stats。"),
        ("一条断言到底检查什么", mono("ksva explain"), "脚本需要结构化结果时使用 parse。"),
    ], [49 * mm, 55 * mm, CONTENT_W - 104 * mm]))

    story.append(heading("安装、环境与首次验证", 1, "installation"))
    story.append(heading("普通用户 host 的推荐环境", 2, "host-environment"))
    story.extend(code_block("""ssh host@192.168.31.116
export KVERIF_HOME=/home/host/kverif
export PATH="$KVERIF_HOME/tools:$PATH"
export PYTHON=/usr/local/bin/python3.8
export VERDI_HOME=/home/synopsys/verdi/Verdi_O-2018.09-SP2
export VCS_HOME=/home/synopsys/vcs/O-2018.09-SP2

/home/host/kverif/tools/kverif doctor
/home/host/kverif/tools/kverif tutorial waveform
/home/host/kverif/tools/kverif tasks""", "Bash / Zsh"))
    story.extend(code_block("""setenv KVERIF_HOME /home/host/kverif
setenv PATH "$KVERIF_HOME/tools:$PATH"
setenv VERDI_HOME /home/synopsys/verdi/Verdi_O-2018.09-SP2
setenv PYTHON /usr/local/bin/python3.8
setenv VCS_HOME /home/synopsys/vcs/O-2018.09-SP2

/home/host/kverif/tools/kverif doctor
/home/host/kverif/tools/kverif tutorial waveform""", "csh / tcsh"))
    story.append(heading("复制到另一台机器前要知道什么", 2, "deployment-boundary"))
    story.append(callout(
        "不能只复制一个 kdebug 文件",
        "tools/kdebug 只是命令入口，运行时还需要同一版本的 KVerif 程序、Verdi/VCS、Tcl NPI 库和相应许可证。"
        "纯 Python 工具也需要兼容的 Python。迁移到新机器时应复制完整 KVerif 目录；用户脚本仍只调用 tools 目录中的命令。",
        "warn",
    ))
    story.append(data_table(["检查", "命令", "期望"], [
        ("新手环境检查", mono("/home/host/kverif/tools/kverif doctor"), "required failures 为 0。"),
        ("真实 FSDB 教程", mono("... kverif tutorial waveform"), "Tutorial checks: PASS。"),
        ("KDebug 操作列表", mono("/home/host/kverif/tools/kdebug actions --json"), "ok=true，并列出当前支持的操作。"),
        ("KDebug NPI", mono("... kdebug --json action npi.capabilities"), "列出当前 Verdi 能找到哪些 NPI 命令。"),
        ("KCov 假数据", mono("... kcov cov-holes --vdb fake --fake --json"), "无需 EDA 许可证即可检查命令行是否可用。"),
        ("KBit", mono("... kbit conv 8'hff --json"), "width=8，unsigned=255。"),
        ("LSF/MCP", mono("... kverif-lsf-doctor --fake"), "process_started/actions_ok/quit_ok。"),
    ], [33 * mm, 82 * mm, CONTENT_W - 115 * mm], small=True))

    story.append(heading("怎样调用工具、怎样读取结果", 1, "common-contract"))
    story.append(heading("命令行和 JSON 两种写法", 2, "cli-vs-json"))
    story.append(p(
        "人在终端里通常直接写命令行参数；脚本需要保存或批量生成请求时，也可以提交完整 JSON。"
        f"{mono('--json')} 只表示“把结果输出为 JSON”，不是让你提供一个名为 json 的文件。"
    ))
    story.extend(code_block("""# 同一查询的参数式写法
/home/host/kverif/tools/kdebug --json value-at \\
  --fsdb /proj/out/waves.fsdb --signal top.clk --time 10ns

# 完整 JSON 从 stdin 输入；最后一个 - 表示 stdin
printf '%s\n' '{"api_version":"kdebug.v1","action":"value.at","target":{"fsdb":"/proj/out/waves.fsdb"},"args":{"signal":"top.clk","time":"10ns"}}' \\
  | /home/host/kverif/tools/kdebug --json -""", "对照示例"))
    story.append(heading("JSON 请求里各字段是什么意思", 2, "request-envelope"))
    story.append(data_table(["字段", "要求", "含义"], [
        (mono("api_version"), "必填", mono("kdebug.v1")),
        (mono("request_id"), "可选", "由调用脚本填写，用来把请求和返回结果对应起来。"),
        (mono("action"), "必填", "要执行的操作名。"),
        (mono("target"), "按操作填写", "输入文件或会话，例如 daidir、fsdb、session_id。"),
        (mono("args"), "按操作填写", "模块名、信号名、时间等功能参数。"),
        (mono("limits"), "可选", "最多返回多少项、最多查多深等数量限制。"),
        (mono("output"), "可选", "输出格式、详细程度等设置。"),
    ], [45 * mm, 28 * mm, CONTENT_W - 73 * mm]))
    story.append(heading("JSON 返回结果里各字段是什么意思", 2, "response-envelope"))
    story.append(data_table(["字段", "怎样使用"], [
        (mono("ok"), "第一步先看它。true 表示成功；false 表示失败。"),
        (mono("action / request_id"), "确认这份结果对应哪项操作、哪次请求。"),
        (mono("summary"), "简要结果，例如找到多少项、返回多少项、是否截断。"),
        (mono("data"), "详细结果，例如对象列表、依赖图或事务列表。"),
        (mono("findings / warnings"), "补充说明。即使 ok=true，也要留意这里是否提示结果不完整。"),
        (mono("error.code / message"), "失败原因。脚本应优先按 error.code 分类，不要只匹配文字。"),
        (mono("meta"), "运行后端、耗时和截断状态等附加信息。"),
    ], [52 * mm, CONTENT_W - 52 * mm]))

    story.append(heading("KDebug 命令和通用参数", 1, "kdebug-cli"))
    story.append(heading("常用快捷命令", 2, "kdebug-shortcuts"))
    shortcut_rows = [(mono(name), esc(purpose), mono(tail)) for name, purpose, tail in KDEBUG_SHORTCUTS]
    story.append(data_table(["命令", "用途", "参数"], shortcut_rows,
                            [39 * mm, 45 * mm, CONTENT_W - 84 * mm], small=True))
    story.append(heading("快捷命令通用参数", 2, "kdebug-shortcut-options"))
    story.append(data_table(["参数", "填写内容", "写入的 JSON 字段"],
                            [(mono(a), esc(b), esc(c)) for a, b, c in KDEBUG_CLI_OPTIONS],
                            [51 * mm, 35 * mm, CONTENT_W - 86 * mm], small=True))
    story.append(heading("功能参数汇总", 2, "kdebug-common-fields"))
    story.append(p(
        "下表汇总所有操作可能用到的功能参数。每项操作只需要其中一部分；具体要填哪些参数，请看对应操作页面。"
    ))
    union_samples: dict[str, Any] = {}
    required_fields: set[str] = set()
    for action in actions:
        request = read_json(choose_example(action, "request"))
        required_fields.update(action.get("required_args") or [])
        for key, value in (request.get("args") or {}).items():
            union_samples.setdefault(key, value)
    rows = []
    for key in sorted(set(union_samples) | required_fields):
        sample = union_samples.get(key)
        rows.append((mono(f"args.{key}"), esc(infer_type(sample)), "至少一项必填" if key in required_fields else "可选",
                     esc(FIELD_DESCRIPTIONS.get(key, "该参数只用于部分操作，具体含义见对应操作页面。")), sample_text(sample)))
    story.append(data_table(["字段", "类型", "要求", "含义", "示例"], rows,
                            [34 * mm, 19 * mm, 22 * mm, 62 * mm, CONTENT_W - 137 * mm], small=True))
    target_keys = sorted({key for action in actions for key in (read_json(choose_example(action, "request")).get("target") or {})} | set(TARGET_DESCRIPTIONS))
    story.append(heading("输入、数量限制和输出设置", 2, "target-limits-output"))
    target_rows = [(mono(f"target.{key}"), esc(TARGET_DESCRIPTIONS.get(key, "扩展 target 字段。"))) for key in target_keys]
    limit_rows = [(mono(f"limits.{key}"), esc(desc)) for key, desc in LIMIT_DESCRIPTIONS.items()]
    output_rows = [(mono(f"output.{key}"), esc(desc)) for key, desc in OUTPUT_DESCRIPTIONS.items()]
    story.append(data_table(["target 字段", "含义"], target_rows, [54 * mm, CONTENT_W - 54 * mm], small=True))
    story.append(Spacer(1, 4))
    story.append(data_table(["limits 字段", "含义"], limit_rows, [54 * mm, CONTENT_W - 54 * mm], small=True))
    story.append(Spacer(1, 4))
    story.append(data_table(["output 字段", "含义"], output_rows, [54 * mm, CONTENT_W - 54 * mm], small=True))
    story.append(heading("操作快速索引", 2, "kdebug-action-index"))
    index_rows = []
    for action in actions:
        index_rows.append((
            Paragraph(f'<link href="#action-{slug(action["name"])}">{mono(action["name"])}</link>', STYLES["TableCell"]),
            esc(action["category"]), esc(action["status"]), esc(action["requires"]),
        ))
    story.append(data_table(["操作名", "分类", "状态", "需要的输入"], index_rows,
                            [62 * mm, 32 * mm, 34 * mm, CONTENT_W - 128 * mm], small=True))
    story.append(callout(
        "本版操作数量",
        " / ".join(f"{esc(name)}={count}" for name, count in sorted(category_counts.items())),
        "note",
    ))

    make_task_coverage_audit(story)
    make_module_instance_demo(story)
    make_ports_connectivity_demo(story)
    make_hierarchy_demo(story)
    make_internal_objects_demo(story)
    make_language_netlist_demo(story)
    make_source_modification_demo(story)
    make_environment_crdb_demo(story)
    make_writer_power_demo(story)

    story.append(heading("KDebug 操作参考", 1, "kdebug-actions"))
    kdebug_action_reference(story, actions, tests)

    make_kcov_sections(story)
    make_kbit_sections(story)
    make_kentry_sections(story)
    make_kloc_sections(story)
    make_ksva_sections(story)
    make_kberif_sections(story)
    make_keda_sections(story)
    make_loop_mcp_sections(story)
    make_secondary_development(story)
    make_security_testing(story, stress)
    make_appendices(story, actions)
    return story


def validate_pdf(pdf_path: Path, actions: list[dict[str, Any]]) -> dict[str, Any]:
    import pdfplumber
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    outlines = reader.outline
    annotation_count = 0
    link_count = 0
    for page in reader.pages:
        annots = page.get("/Annots") or []
        annotation_count += len(annots)
        for ref in annots:
            try:
                annot = ref.get_object()
                if annot.get("/Subtype") == "/Link":
                    link_count += 1
            except Exception:
                pass

    all_text_parts = []
    blank_pages = []
    sparse_pages = []
    overflow_words = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page_no, page in enumerate(pdf.pages, 1):
            text = page.extract_text() or ""
            all_text_parts.append(text)
            body_text = page.crop((0, 14 * mm, page.width, page.height - 14 * mm)).extract_text() or ""
            body_char_count = len(re.sub(r"\s+", "", body_text))
            if body_char_count < 8:
                blank_pages.append(page_no)
            elif body_char_count < 24:
                sparse_pages.append({"page": page_no, "body_char_count": body_char_count, "text": body_text[:120]})
            for word in page.extract_words():
                if word["x0"] < -0.5 or word["x1"] > page.width + 0.5 or word["top"] < -0.5 or word["bottom"] > page.height + 0.5:
                    overflow_words.append({"page": page_no, "text": word["text"], "x0": word["x0"], "x1": word["x1"]})

    all_text = "\n".join(all_text_parts)
    missing_actions = [item["name"] for item in actions if item["name"] not in all_text]
    action_names = {item["name"] for item in actions}
    workflow_actions = {name for item in WORKFLOW_COVERAGE for name in item["actions"]}
    workflow_kinds = {name for item in WORKFLOW_COVERAGE for name in item["kinds"]}
    missing_workflow_titles = [item["title"] for item in WORKFLOW_COVERAGE if item["title"] not in all_text]
    unknown_workflow_actions = sorted(workflow_actions - action_names)
    uncovered_npi_actions = sorted(NPI_WORKFLOW_ACTIONS - workflow_actions)
    unexpected_npi_actions = sorted(workflow_actions - NPI_WORKFLOW_ACTIONS)
    uncovered_module_kinds = sorted(MODULE_OBJECT_KINDS - workflow_kinds)
    unexpected_module_kinds = sorted(workflow_kinds - MODULE_OBJECT_KINDS)
    expected_tools = ["KVerif Task CLI", "KDebug", "KCov", "KBit", "KEntry", "KLoc", "KSVA", "KBerif", "KEDA Runner", "Loop Wrapper", "KVerif MCP"]
    missing_tools = [tool for tool in expected_tools if tool not in all_text]
    beginner_commands = [
        "kverif doctor",
        "kverif tutorial waveform",
        "kverif tutorial module-inspect",
        "kverif inspect-module",
        "kverif trace-signal",
        "kverif new signal-check",
    ]
    missing_beginner_commands = [command for command in beginner_commands if command not in all_text]
    forbidden_unicode = sorted({
        f"U+{ord(char):04X}" for char in all_text
        if char == "\u200b" or 0x2010 <= ord(char) <= 0x2015
    })
    local_path_hits = sorted(set(re.findall(
        r"(?i)(?<![A-Za-z0-9_./-])(?:[A-Z]:[/\\][^\s\"'}]+)", all_text,
    )))[:20]
    secret_shape_hits = sorted(set(re.findall(
        r"(?i)(?:sk-[A-Za-z0-9]{16,}|api[_ -]?key\s*[:=]\s*[A-Za-z0-9:_-]{16,})",
        all_text,
    )))[:5]
    unclear_phrases = [
        "消费 summary",
        "公共合同",
        "输出合同",
        "派生结论",
        "证据链",
        "稳定边界",
        "canonical response",
        "canonical 示例",
        "action 特有字段",
        "能力探针",
        "专项模型",
        "public tool groups",
        "public executable",
        "CLI-only Integration Guide",
        "SDK-free",
        "one-shot",
        "聚合 action",
        "权威输入",
    ]
    unclear_phrase_hits = [phrase for phrase in unclear_phrases if phrase in all_text]
    sha = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    result = {
        "schema": "kverif.secondary-manual.audit.v1",
        "pdf": pdf_path.relative_to(ROOT).as_posix(),
        "sha256": sha,
        "bytes": pdf_path.stat().st_size,
        "pages": len(reader.pages),
        "outline_root_items": len(outlines),
        "annotations": annotation_count,
        "link_annotations": link_count,
        "active_kdebug_actions_expected": len(actions),
        "task_workflows_expected": len(WORKFLOW_COVERAGE),
        "task_workflows_present": len(WORKFLOW_COVERAGE) - len(missing_workflow_titles),
        "npi_workflow_actions_expected": len(NPI_WORKFLOW_ACTIONS),
        "npi_workflow_actions_mapped": len(NPI_WORKFLOW_ACTIONS) - len(uncovered_npi_actions),
        "module_object_kinds_expected": len(MODULE_OBJECT_KINDS),
        "module_object_kinds_mapped": len(MODULE_OBJECT_KINDS) - len(uncovered_module_kinds),
        "missing_actions": missing_actions,
        "missing_tools": missing_tools,
        "beginner_commands_expected": len(beginner_commands),
        "beginner_commands_present": len(beginner_commands) - len(missing_beginner_commands),
        "missing_beginner_commands": missing_beginner_commands,
        "missing_workflow_titles": missing_workflow_titles,
        "unknown_workflow_actions": unknown_workflow_actions,
        "uncovered_npi_actions": uncovered_npi_actions,
        "unexpected_npi_actions": unexpected_npi_actions,
        "uncovered_module_kinds": uncovered_module_kinds,
        "unexpected_module_kinds": unexpected_module_kinds,
        "blank_pages": blank_pages,
        "sparse_pages": sparse_pages,
        "overflow_words": overflow_words[:20],
        "forbidden_unicode": forbidden_unicode,
        "nul_character_count": all_text.count("\x00"),
        "local_path_hits": local_path_hits,
        "secret_shape_hits": secret_shape_hits,
        "unclear_phrase_hits": unclear_phrase_hits,
        "checks": {
            "all_actions_present": not missing_actions,
            "all_tool_groups_present": not missing_tools,
            "all_beginner_commands_present": not missing_beginner_commands,
            "all_task_workflows_present": not missing_workflow_titles,
            "all_workflow_actions_exist": not unknown_workflow_actions,
            "all_npi_actions_mapped_to_workflows": not uncovered_npi_actions and not unexpected_npi_actions,
            "all_module_object_kinds_mapped_to_workflows": not uncovered_module_kinds and not unexpected_module_kinds,
            "clickable_links_present": link_count > 20,
            "bookmarks_present": len(outlines) > 5,
            "no_blank_pages": not blank_pages,
            "no_sparse_pages": not sparse_pages,
            "no_text_overflow": not overflow_words,
            "no_zero_width_or_unicode_dash": not forbidden_unicode,
            "no_missing_glyph_nuls": "\x00" not in all_text,
            "no_local_windows_paths": not local_path_hits,
            "no_secret_shapes": not secret_shape_hits,
            "plain_language_terms": not unclear_phrase_hits,
            "reasonable_page_count": 80 <= len(reader.pages) <= 400,
        },
    }
    result["ok"] = all(result["checks"].values())
    return result


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    actions = load_actions()
    tests = inventory_tests()
    stress_path = ROOT / "kdebug" / "tests" / "vm" / "npi_actions" / "evidence" / "stress-summary.json"
    stress = read_json(stress_path)

    missing_copy = sorted(item["name"] for item in actions if item["name"] not in ACTION_PURPOSE)
    if missing_copy:
        raise RuntimeError(f"missing ACTION_PURPOSE entries: {missing_copy}")

    doc = ManualDocTemplate(
        str(OUT_PDF), pagesize=A4,
        leftMargin=LEFT, rightMargin=RIGHT, topMargin=TOP, bottomMargin=BOTTOM,
        title="KVerif 新手上手与二次开发手册",
        author="KVerif Project",
        subject="KVerif 新手教程、二次开发、命令参数与实测示例",
    )
    story = build_story(actions, tests, stress)
    doc.multiBuild(story)

    audit = validate_pdf(OUT_PDF, actions)
    AUDIT_JSON.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    return 0 if audit["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
