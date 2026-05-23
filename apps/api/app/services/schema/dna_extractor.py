"""
Document DNA Extractor — converts a ParsedDocument into a DocumentDNA schema.

The DNA schema is the central constraint object that all AI generation
and layout validation must respect.
"""
from __future__ import annotations

from pathlib import Path

from ..docx.parser import DOCXParser, ParsedDocument, ParsedParagraph, emu_to_pt
from ..docx.section_detector import SectionDetector, DetectedSection
from .typography_analyzer import estimate_max_chars_per_line, TypographyMetricsService
from ...schemas.dna import (
    DocumentDNA,
    PageMetadata,
    SectionSchema,
    BulletSchema,
    TypographyMetadata,
    SpacingMetadata,
    ConstraintMetadata,
)

_typography_service = TypographyMetricsService()


def _build_typography(para: ParsedParagraph) -> TypographyMetadata:
    return TypographyMetadata(
        font_family=para.font.family,
        font_size=para.font.size_pt,
        bold=para.font.bold,
        italic=para.font.italic,
        color=para.font.color,
        all_caps=para.font.all_caps,
        alignment=para.alignment,
    )


def _build_spacing(para: ParsedParagraph) -> SpacingMetadata:
    return SpacingMetadata(
        space_before_pt=para.spacing.space_before_pt,
        space_after_pt=para.spacing.space_after_pt,
        line_spacing=para.spacing.line_spacing_pt,
        line_spacing_rule=para.spacing.line_spacing_rule,
    )


def _build_constraint(
    para: ParsedParagraph,
    usable_width_pt: float,
    max_lines: int = 2,
) -> ConstraintMetadata:
    indent_pt = emu_to_pt(para.indent_left_emu)
    max_chars = estimate_max_chars_per_line(
        font_family=para.font.family,
        font_size_pt=para.font.size_pt,
        usable_width_pt=usable_width_pt,
        bold=para.font.bold,
        indent_left_pt=indent_pt,
    )
    return ConstraintMetadata(
        max_lines_per_bullet=max_lines,
        max_chars_per_line=max_chars,
        usable_width_pt=round(usable_width_pt, 2),
        indent_left_pt=round(indent_pt, 2),
        estimated_chars_per_line=max_chars,
    )


def _find_representative_bullet(
    section: DetectedSection,
    usable_width_pt: float,
) -> BulletSchema:
    """Find the most representative bullet-style paragraph in a section."""
    body_paras = [p for p in section.body_paragraphs if not p.is_empty]
    if not body_paras:
        # Default bullet schema
        dummy = section.header_paragraph
        return BulletSchema(
            style_name="Normal",
            typography=_build_typography(dummy),
            spacing=_build_spacing(dummy),
            indent_left_emu=0,
            constraints=_build_constraint(dummy, usable_width_pt),
        )

    # Pick paragraph most likely to be a bullet (deepest indent, smallest font)
    candidate = min(
        body_paras,
        key=lambda p: (-p.indent_left_emu, -p.font.size_pt),
    )
    # Infer max_lines from spacing — tightly spaced resumes use 1-2 lines
    space_total = (
        candidate.spacing.space_before_pt + candidate.spacing.space_after_pt
    )
    max_lines = 1 if space_total < 2 else 2

    return BulletSchema(
        style_name=candidate.style_name,
        typography=_build_typography(candidate),
        spacing=_build_spacing(candidate),
        indent_left_emu=candidate.indent_left_emu,
        constraints=_build_constraint(candidate, usable_width_pt, max_lines),
    )


def _classify_template_family(doc: ParsedDocument, sections: list[DetectedSection]) -> str:
    """Heuristically classify the template family."""
    page_height_in = doc.page.height_emu / 914400
    section_names = {s.name.lower() for s in sections}
    has_positions = any(
        "position" in n or "responsibilit" in n for n in section_names
    )
    # Single-page compact MBA style
    if page_height_in <= 11.5 and has_positions:
        return "mba_placement"
    if page_height_in <= 11.5:
        return "single_page_compact"
    return "multi_page_standard"


class DNAExtractor:
    """
    Orchestrates DOCX parsing → section detection → DNA schema generation.

    Usage:
        extractor = DNAExtractor()
        dna = extractor.extract("path/to/resume.docx")
    """

    def __init__(self):
        self._parser = DOCXParser()
        self._section_detector = SectionDetector()

    def extract(self, file_path: str | Path) -> DocumentDNA:
        doc = self._parser.parse(file_path)
        sections = self._section_detector.detect(doc)
        return self._build_dna(doc, sections)

    def _build_dna(
        self, doc: ParsedDocument, sections: list[DetectedSection]
    ) -> DocumentDNA:
        page = PageMetadata(
            width_emu=doc.page.width_emu,
            height_emu=doc.page.height_emu,
            margin_top_emu=doc.page.margin_top_emu,
            margin_bottom_emu=doc.page.margin_bottom_emu,
            margin_left_emu=doc.page.margin_left_emu,
            margin_right_emu=doc.page.margin_right_emu,
            usable_width_emu=doc.page.usable_width_emu,
        )
        usable_width_pt = doc.page.usable_width_pt

        # Global bullet schema from first experience-like section
        primary_section = next(
            (s for s in sections if s.section_type == "experience"),
            sections[0] if sections else None,
        )
        if primary_section:
            global_bullet_schema = _find_representative_bullet(
                primary_section, usable_width_pt
            )
        else:
            # Fallback: synthesize from doc defaults
            global_bullet_schema = self._default_bullet_schema(doc, usable_width_pt)

        section_schemas = [
            SectionSchema(
                name=s.name,
                section_type=s.section_type,
                order_index=s.order_index,
                style_name=s.header_paragraph.style_name,
                typography=_build_typography(s.header_paragraph),
                spacing=_build_spacing(s.header_paragraph),
                bullet_schema=_find_representative_bullet(s, usable_width_pt),
            )
            for s in sections
        ]

        return DocumentDNA(
            page=page,
            default_font_family=doc.default_font_family,
            default_font_size=doc.default_font_size_pt,
            sections=section_schemas,
            bullet_schema=global_bullet_schema,
            template_family=_classify_template_family(doc, sections),
            raw_section_names=[s.name for s in sections],
        )

    def _default_bullet_schema(
        self, doc: ParsedDocument, usable_width_pt: float
    ) -> BulletSchema:
        from ..docx.parser import ParsedParagraph, ParsedFont, ParsedSpacing

        dummy = ParsedParagraph(
            text="",
            style_name="Normal",
            font=ParsedFont(
                family=doc.default_font_family,
                size_pt=doc.default_font_size_pt,
            ),
            spacing=ParsedSpacing(space_after_pt=3.0),
            is_empty=True,
        )
        return BulletSchema(
            style_name="Normal",
            typography=_build_typography(dummy),
            spacing=_build_spacing(dummy),
            indent_left_emu=0,
            constraints=_build_constraint(dummy, usable_width_pt),
        )
