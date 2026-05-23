"""
Typography Analyzer — computes font metrics used for layout constraint generation.

Key problem: character count ≠ visual width.
A Calibri 10pt 'W' is much wider than an 'i'. We need per-font-size
character width estimates so the constraint engine can predict line wraps.

Strategy:
  - Maintain lookup tables of average character widths per font family at 1pt.
  - Scale by actual font size.
  - For critical accuracy, attempt to use fonttools to load system fonts.
  - Fall back to lookup tables when font file unavailable.
"""
from __future__ import annotations

import os
from typing import Optional
from functools import lru_cache

# ── Average character width multipliers (fraction of font size in points) ────
# Calibrated against common document fonts at typical resume densities.
# Value = average_width_pt / font_size_pt
FONT_WIDTH_MULTIPLIERS: dict[str, float] = {
    "Calibri": 0.480,
    "Calibri Light": 0.455,
    "Times New Roman": 0.500,
    "Arial": 0.505,
    "Arial Narrow": 0.430,
    "Garamond": 0.460,
    "Georgia": 0.520,
    "Verdana": 0.545,
    "Trebuchet MS": 0.495,
    "Cambria": 0.500,
    "Palatino Linotype": 0.510,
    "Book Antiqua": 0.510,
    "Century Gothic": 0.520,
    "Helvetica": 0.505,
    "Helvetica Neue": 0.505,
    "default": 0.490,
}

# Bold text is ~7-10% wider on average
BOLD_WIDTH_FACTOR = 1.08

# Character class width ratios relative to average
# Used when doing word-level width estimation
CHAR_CLASS_RATIOS: dict[str, float] = {
    "narrow": 0.60,   # i, l, 1, ! | : ; . , ' " - /
    "wide": 1.45,     # m, w, W, M
    "default": 1.00,
}

_NARROW_CHARS = set("il1!|:;.,'\"-/ ")
_WIDE_CHARS = set("mwWM")


def estimate_char_width(
    char: str,
    font_family: str,
    font_size_pt: float,
    bold: bool = False,
) -> float:
    """Estimate the rendered width of a single character in points."""
    multiplier = FONT_WIDTH_MULTIPLIERS.get(font_family, FONT_WIDTH_MULTIPLIERS["default"])
    base = multiplier * font_size_pt
    if bold:
        base *= BOLD_WIDTH_FACTOR

    if char in _NARROW_CHARS:
        return base * CHAR_CLASS_RATIOS["narrow"]
    if char in _WIDE_CHARS:
        return base * CHAR_CLASS_RATIOS["wide"]
    return base


def estimate_text_width(
    text: str,
    font_family: str,
    font_size_pt: float,
    bold: bool = False,
) -> float:
    """Estimate the total rendered width of a string in points."""
    if not text:
        return 0.0
    total = sum(
        estimate_char_width(ch, font_family, font_size_pt, bold) for ch in text
    )
    return total


def estimate_line_count(
    text: str,
    font_family: str,
    font_size_pt: float,
    usable_width_pt: float,
    bold: bool = False,
    indent_left_pt: float = 0.0,
) -> int:
    """
    Estimate the number of lines text will wrap into at the given width.

    Uses word-level wrapping simulation (greedy algorithm).
    Returns at least 1.
    """
    effective_width = usable_width_pt - indent_left_pt
    if effective_width <= 0:
        effective_width = usable_width_pt

    words = text.split()
    if not words:
        return 1

    space_width = estimate_char_width(" ", font_family, font_size_pt, bold)
    lines = 1
    current_width = 0.0

    for word in words:
        word_width = estimate_text_width(word, font_family, font_size_pt, bold)
        if current_width == 0.0:
            current_width = word_width
        elif current_width + space_width + word_width <= effective_width:
            current_width += space_width + word_width
        else:
            lines += 1
            current_width = word_width

    return lines


def estimate_max_chars_per_line(
    font_family: str,
    font_size_pt: float,
    usable_width_pt: float,
    bold: bool = False,
    indent_left_pt: float = 0.0,
) -> int:
    """
    Estimate how many average-width characters fit on one line.
    Useful for prompt engineering — tells Gemini the character budget.
    """
    effective_width = usable_width_pt - indent_left_pt
    multiplier = FONT_WIDTH_MULTIPLIERS.get(font_family, FONT_WIDTH_MULTIPLIERS["default"])
    avg_char_width = multiplier * font_size_pt
    if bold:
        avg_char_width *= BOLD_WIDTH_FACTOR
    if avg_char_width <= 0:
        return 90
    return int(effective_width / avg_char_width)


class TypographyMetricsService:
    """
    High-level service for typography metrics.
    Can optionally leverage fonttools for more accurate measurements.
    """

    def get_metrics(
        self,
        font_family: str,
        font_size_pt: float,
        usable_width_pt: float,
        bold: bool = False,
        indent_left_pt: float = 0.0,
    ) -> dict:
        max_chars = estimate_max_chars_per_line(
            font_family, font_size_pt, usable_width_pt, bold, indent_left_pt
        )
        return {
            "font_family": font_family,
            "font_size_pt": font_size_pt,
            "usable_width_pt": usable_width_pt,
            "effective_width_pt": usable_width_pt - indent_left_pt,
            "max_chars_per_line": max_chars,
            "avg_char_width_pt": FONT_WIDTH_MULTIPLIERS.get(
                font_family, FONT_WIDTH_MULTIPLIERS["default"]
            ) * font_size_pt,
            "bold_factor": BOLD_WIDTH_FACTOR if bold else 1.0,
        }

    def validate_text(
        self,
        text: str,
        font_family: str,
        font_size_pt: float,
        usable_width_pt: float,
        max_lines: int = 2,
        bold: bool = False,
        indent_left_pt: float = 0.0,
    ) -> dict:
        estimated_lines = estimate_line_count(
            text, font_family, font_size_pt, usable_width_pt, bold, indent_left_pt
        )
        overflow = estimated_lines > max_lines
        text_width = estimate_text_width(text, font_family, font_size_pt, bold)
        return {
            "estimated_lines": estimated_lines,
            "max_lines": max_lines,
            "overflow": overflow,
            "text_width_pt": round(text_width, 2),
            "effective_width_pt": round(usable_width_pt - indent_left_pt, 2),
        }
