"""
Layout Constraint Engine — the core of ResumeOS's layout-preservation system.

Responsibilities:
  1. Build a LayoutConstraintSet from a DocumentDNA.
  2. Validate candidate text against constraints.
  3. Report overflow details.

The engine uses typography metrics to simulate rendering without needing
LibreOffice for every validation pass.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ...schemas.dna import DocumentDNA, BulletSchema, ConstraintMetadata
from ..schema.typography_analyzer import (
    estimate_line_count,
    estimate_text_width,
    estimate_max_chars_per_line,
)


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class ConstraintViolation:
    field: str
    expected: str
    actual: str
    severity: str = "error"  # "error" | "warning"


@dataclass
class ValidationResult:
    is_valid: bool
    estimated_lines: int
    max_lines: int
    overflow: bool
    overflow_lines: int = 0
    violations: list[ConstraintViolation] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)


@dataclass
class SectionConstraints:
    section_name: str
    section_type: str
    font_family: str
    font_size_pt: float
    bold: bool
    usable_width_pt: float
    indent_left_pt: float
    max_lines_per_bullet: int
    max_chars_per_line: int
    space_after_pt: float = 3.0


# ── Engine ────────────────────────────────────────────────────────────────────

class LayoutConstraintEngine:
    """
    Builds and validates layout constraints from a DocumentDNA.

    Design principles:
      - Pure Python, no LibreOffice dependency for inline validation.
      - Conservative: if in doubt, flag as potential overflow.
      - Per-section constraints (different sections may have different fonts).
    """

    def __init__(self, dna: DocumentDNA):
        self._dna = dna
        self._section_map: dict[str, SectionConstraints] = {}
        self._global_constraints = self._build_global_constraints(dna)
        self._build_section_map(dna)

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build_global_constraints(self, dna: DocumentDNA) -> SectionConstraints:
        bs = dna.bullet_schema
        return SectionConstraints(
            section_name="__global__",
            section_type="generic",
            font_family=bs.typography.font_family,
            font_size_pt=bs.typography.font_size,
            bold=bs.typography.bold,
            usable_width_pt=dna.page.usable_width_pt,
            indent_left_pt=bs.constraints.indent_left_pt,
            max_lines_per_bullet=bs.constraints.max_lines_per_bullet,
            max_chars_per_line=bs.constraints.max_chars_per_line,
            space_after_pt=bs.spacing.space_after_pt,
        )

    def _build_section_map(self, dna: DocumentDNA) -> None:
        for section in dna.sections:
            if section.bullet_schema:
                bs = section.bullet_schema
                self._section_map[section.name.lower()] = SectionConstraints(
                    section_name=section.name,
                    section_type=section.section_type,
                    font_family=bs.typography.font_family,
                    font_size_pt=bs.typography.font_size,
                    bold=bs.typography.bold,
                    usable_width_pt=dna.page.usable_width_pt,
                    indent_left_pt=bs.constraints.indent_left_pt,
                    max_lines_per_bullet=bs.constraints.max_lines_per_bullet,
                    max_chars_per_line=bs.constraints.max_chars_per_line,
                    space_after_pt=bs.spacing.space_after_pt,
                )

    # ── Lookup ────────────────────────────────────────────────────────────────

    def get_constraints(self, section_name: Optional[str] = None) -> SectionConstraints:
        if section_name:
            key = section_name.lower()
            if key in self._section_map:
                return self._section_map[key]
        return self._global_constraints

    # ── Validation ────────────────────────────────────────────────────────────

    def validate_bullet(
        self,
        text: str,
        section_name: Optional[str] = None,
        override_max_lines: Optional[int] = None,
    ) -> ValidationResult:
        constraints = self.get_constraints(section_name)
        max_lines = override_max_lines or constraints.max_lines_per_bullet

        estimated_lines = estimate_line_count(
            text=text,
            font_family=constraints.font_family,
            font_size_pt=constraints.font_size_pt,
            usable_width_pt=constraints.usable_width_pt,
            bold=constraints.bold,
            indent_left_pt=constraints.indent_left_pt,
        )

        overflow = estimated_lines > max_lines
        overflow_lines = max(0, estimated_lines - max_lines)
        violations: list[ConstraintViolation] = []
        warnings: list[str] = []

        if overflow:
            violations.append(
                ConstraintViolation(
                    field="line_count",
                    expected=f"<= {max_lines}",
                    actual=str(estimated_lines),
                    severity="error",
                )
            )

        # Soft warning: within 10% of max chars
        char_count = len(text)
        max_chars = constraints.max_chars_per_line * max_lines
        if char_count > max_chars * 0.9 and not overflow:
            warnings.append(
                f"Text is {char_count} chars, close to limit of ~{max_chars}. "
                "Verify layout after export."
            )

        metrics = {
            "estimated_lines": estimated_lines,
            "max_lines": max_lines,
            "char_count": char_count,
            "max_chars_estimate": max_chars,
            "font_family": constraints.font_family,
            "font_size_pt": constraints.font_size_pt,
            "usable_width_pt": constraints.usable_width_pt,
            "indent_left_pt": constraints.indent_left_pt,
        }

        return ValidationResult(
            is_valid=not overflow,
            estimated_lines=estimated_lines,
            max_lines=max_lines,
            overflow=overflow,
            overflow_lines=overflow_lines,
            violations=violations,
            warnings=warnings,
            metrics=metrics,
        )

    def validate_alternatives(
        self,
        alternatives: list[str],
        section_name: Optional[str] = None,
    ) -> list[dict]:
        """Validate a list of candidate alternatives and rank them."""
        results = []
        for alt in alternatives:
            result = self.validate_bullet(alt, section_name)
            results.append({
                "text": alt,
                "valid": result.is_valid,
                "estimated_lines": result.estimated_lines,
                "overflow": result.overflow,
                "warnings": result.warnings,
                "char_count": len(alt),
            })
        # Sort: valid first, then by line count ascending
        results.sort(key=lambda r: (r["overflow"], r["estimated_lines"]))
        return results

    def get_prompt_constraints(self, section_name: Optional[str] = None) -> dict:
        """Returns constraint dict suitable for injection into AI prompts."""
        c = self.get_constraints(section_name)
        return {
            "max_lines": c.max_lines_per_bullet,
            "max_chars_per_line": c.max_chars_per_line,
            "font_family": c.font_family,
            "font_size": c.font_size_pt,
            "usable_width_pt": round(c.usable_width_pt, 1),
            "indent_left_pt": round(c.indent_left_pt, 1),
        }
