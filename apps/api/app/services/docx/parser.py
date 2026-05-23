"""
DOCX Parser — extracts raw structure from .docx files.

Outputs a structured ParsedDocument containing all paragraphs with their
full typography and spacing metadata. Section detection is a separate pass.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Pt


# ── EMU ↔ unit helpers ────────────────────────────────────────────────────────
_EMU_PER_PT = 12700
_EMU_PER_INCH = 914400
_EMU_PER_CM = 360000


def emu_to_pt(emu: int) -> float:
    return emu / _EMU_PER_PT


def emu_to_inches(emu: int) -> float:
    return emu / _EMU_PER_INCH


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class ParsedFont:
    family: str = "Calibri"
    size_pt: float = 10.0
    bold: bool = False
    italic: bool = False
    color: Optional[str] = None  # hex without #
    all_caps: bool = False
    underline: bool = False


@dataclass
class ParsedSpacing:
    space_before_pt: float = 0.0
    space_after_pt: float = 0.0
    line_spacing_pt: Optional[float] = None
    line_spacing_rule: Optional[str] = None  # "auto", "exact", "atLeast"


@dataclass
class ParsedParagraph:
    text: str
    style_name: str
    font: ParsedFont
    spacing: ParsedSpacing
    alignment: str = "left"
    indent_left_emu: int = 0
    indent_right_emu: int = 0
    indent_hanging_emu: int = 0
    is_empty: bool = False
    raw_xml: Optional[str] = None


@dataclass
class ParsedPage:
    width_emu: int = 12192000
    height_emu: int = 15840000
    margin_top_emu: int = 720000
    margin_bottom_emu: int = 720000
    margin_left_emu: int = 1080000
    margin_right_emu: int = 1080000

    @property
    def usable_width_emu(self) -> int:
        return self.width_emu - self.margin_left_emu - self.margin_right_emu

    @property
    def usable_width_pt(self) -> float:
        return emu_to_pt(self.usable_width_emu)


@dataclass
class ParsedDocument:
    page: ParsedPage = field(default_factory=ParsedPage)
    paragraphs: list[ParsedParagraph] = field(default_factory=list)
    default_font_family: str = "Calibri"
    default_font_size_pt: float = 10.0


# ── Parser ────────────────────────────────────────────────────────────────────

class DOCXParser:
    """Parses a .docx file into a ParsedDocument."""

    def parse(self, file_path: str | Path) -> ParsedDocument:
        doc = Document(str(file_path))
        page = self._parse_page(doc)
        default_font = self._get_default_font(doc)
        paragraphs = [
            self._parse_paragraph(p, default_font) for p in doc.paragraphs
        ]
        return ParsedDocument(
            page=page,
            paragraphs=paragraphs,
            default_font_family=default_font.family,
            default_font_size_pt=default_font.size_pt,
        )

    # ── Page / section properties ─────────────────────────────────────────────

    def _parse_page(self, doc: Document) -> ParsedPage:
        sect = doc.sections[0]
        return ParsedPage(
            width_emu=sect.page_width or 12192000,
            height_emu=sect.page_height or 15840000,
            margin_top_emu=sect.top_margin or 720000,
            margin_bottom_emu=sect.bottom_margin or 720000,
            margin_left_emu=sect.left_margin or 1080000,
            margin_right_emu=sect.right_margin or 1080000,
        )

    # ── Default font ─────────────────────────────────────────────────────────

    def _get_default_font(self, doc: Document) -> ParsedFont:
        try:
            normal_style = doc.styles["Normal"]
            font = normal_style.font
            return ParsedFont(
                family=font.name or "Calibri",
                size_pt=font.size.pt if font.size else 10.0,
                bold=bool(font.bold),
                italic=bool(font.italic),
            )
        except Exception:
            return ParsedFont()

    # ── Paragraph parsing ─────────────────────────────────────────────────────

    def _parse_paragraph(self, para, default_font: ParsedFont) -> ParsedParagraph:
        text = para.text
        font = self._extract_paragraph_font(para, default_font)
        spacing = self._extract_spacing(para)
        alignment = self._extract_alignment(para)
        fmt = para.paragraph_format

        return ParsedParagraph(
            text=text,
            style_name=para.style.name if para.style else "Normal",
            font=font,
            spacing=spacing,
            alignment=alignment,
            indent_left_emu=int(fmt.left_indent or 0),
            indent_right_emu=int(fmt.right_indent or 0),
            indent_hanging_emu=int(fmt.first_line_indent or 0)
            if (fmt.first_line_indent and fmt.first_line_indent < 0)
            else 0,
            is_empty=not text.strip(),
        )

    def _extract_paragraph_font(
        self, para, default_font: ParsedFont
    ) -> ParsedFont:
        """
        Resolve the effective font for a paragraph.
        Priority: run-level → paragraph-level → style-level → default.
        We use the first non-empty run as the representative font.
        """
        # Try first non-empty run
        for run in para.runs:
            if run.text.strip():
                return self._extract_run_font(run, default_font)

        # Fall back to paragraph-level style font
        try:
            style_font = para.style.font
            family = style_font.name or default_font.family
            size_pt = style_font.size.pt if style_font.size else default_font.size_pt
            bold = style_font.bold if style_font.bold is not None else default_font.bold
            italic = (
                style_font.italic if style_font.italic is not None else default_font.italic
            )
            color = self._extract_font_color(style_font)
            return ParsedFont(
                family=family,
                size_pt=size_pt,
                bold=bool(bold),
                italic=bool(italic),
                color=color,
            )
        except Exception:
            return default_font

    def _extract_run_font(self, run, default_font: ParsedFont) -> ParsedFont:
        font = run.font
        family = font.name or default_font.family
        size_pt = font.size.pt if font.size else default_font.size_pt
        bold = font.bold if font.bold is not None else default_font.bold
        italic = font.italic if font.italic is not None else default_font.italic
        color = self._extract_font_color(font)
        all_caps = bool(font.all_caps) if font.all_caps is not None else False
        return ParsedFont(
            family=family,
            size_pt=size_pt,
            bold=bool(bold),
            italic=bool(italic),
            color=color,
            all_caps=all_caps,
        )

    def _extract_font_color(self, font) -> Optional[str]:
        try:
            rgb = font.color.rgb
            return str(rgb) if rgb else None
        except Exception:
            return None

    def _extract_spacing(self, para) -> ParsedSpacing:
        fmt = para.paragraph_format
        space_before = float(fmt.space_before.pt) if fmt.space_before else 0.0
        space_after = float(fmt.space_after.pt) if fmt.space_after else 0.0

        line_spacing_pt = None
        line_spacing_rule = None
        if fmt.line_spacing:
            if isinstance(fmt.line_spacing, (int, float)):
                # Could be a multiplier (e.g. 1.15) or EMU value
                if fmt.line_spacing > 100:
                    line_spacing_pt = emu_to_pt(int(fmt.line_spacing))
                    line_spacing_rule = "exact"
                else:
                    line_spacing_pt = fmt.line_spacing
                    line_spacing_rule = "auto"

        return ParsedSpacing(
            space_before_pt=space_before,
            space_after_pt=space_after,
            line_spacing_pt=line_spacing_pt,
            line_spacing_rule=line_spacing_rule,
        )

    def _extract_alignment(self, para) -> str:
        align_map = {
            WD_ALIGN_PARAGRAPH.LEFT: "left",
            WD_ALIGN_PARAGRAPH.CENTER: "center",
            WD_ALIGN_PARAGRAPH.RIGHT: "right",
            WD_ALIGN_PARAGRAPH.JUSTIFY: "justify",
        }
        return align_map.get(para.alignment, "left")
