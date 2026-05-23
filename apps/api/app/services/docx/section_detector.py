"""
Section Detector — identifies resume sections from parsed paragraphs.

Heuristics for MBA-style resumes:
  - Section headers are typically Bold, ALL-CAPS or Title-Case short lines
  - They use Heading styles OR have distinctively larger/bolder typography
  - Bullet content follows headers and uses smaller body font
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from .parser import ParsedDocument, ParsedParagraph, ParsedFont

# Common MBA resume section names
KNOWN_SECTION_NAMES = {
    "education", "experience", "work experience", "professional experience",
    "internships", "internship", "projects", "academic projects",
    "leadership", "leadership & activities", "activities",
    "skills", "technical skills", "certifications", "awards",
    "publications", "research", "summary", "objective", "profile",
    "extracurriculars", "co-curriculars", "achievements",
    "positions of responsibility", "volunteer", "interests",
}

SECTION_TYPE_MAP = {
    "education": "education",
    "experience": "experience",
    "work experience": "experience",
    "professional experience": "experience",
    "internships": "experience",
    "internship": "experience",
    "projects": "projects",
    "academic projects": "projects",
    "leadership": "leadership",
    "leadership & activities": "leadership",
    "activities": "activities",
    "skills": "skills",
    "technical skills": "skills",
    "certifications": "certifications",
    "awards": "awards",
    "summary": "summary",
    "objective": "summary",
    "profile": "summary",
}


@dataclass
class DetectedSection:
    name: str
    section_type: str
    order_index: int
    header_paragraph: ParsedParagraph
    body_paragraphs: list[ParsedParagraph] = field(default_factory=list)


@dataclass
class DetectedBullet:
    text: str
    paragraph: ParsedParagraph
    order_index: int


@dataclass
class DetectedEntry:
    """A role/company/degree block within a section."""
    title_line: Optional[str]
    subtitle_line: Optional[str]
    date_line: Optional[str]
    bullets: list[DetectedBullet] = field(default_factory=list)


class SectionDetector:
    """
    Detects resume sections from a ParsedDocument.

    Strategy:
    1. Walk paragraphs; detect section header candidates.
    2. Assign body paragraphs to preceding header.
    3. Classify each section type.
    """

    def __init__(self, font_size_threshold: float = 0.5):
        # A paragraph's font must be >= body_font + threshold to be a header candidate
        self.font_size_threshold = font_size_threshold

    def detect(self, doc: ParsedDocument) -> list[DetectedSection]:
        # Filter empties
        paras = [p for p in doc.paragraphs if not p.is_empty]
        if not paras:
            return []

        body_font_size = self._estimate_body_font_size(paras)
        sections: list[DetectedSection] = []
        current_section: Optional[DetectedSection] = None

        for idx, para in enumerate(paras):
            if self._is_section_header(para, body_font_size):
                name = para.text.strip()
                section_type = self._classify_section_type(name)
                current_section = DetectedSection(
                    name=name,
                    section_type=section_type,
                    order_index=len(sections),
                    header_paragraph=para,
                )
                sections.append(current_section)
            elif current_section is not None:
                current_section.body_paragraphs.append(para)
            else:
                # Content before first section header — treat as header info
                # (contact info, name) — create implicit top section
                if not sections:
                    current_section = DetectedSection(
                        name="Header",
                        section_type="contact",
                        order_index=0,
                        header_paragraph=para,
                    )
                    sections.append(current_section)
                else:
                    sections[0].body_paragraphs.append(para)

        return sections

    # ── Header detection heuristics ───────────────────────────────────────────

    def _is_section_header(self, para: ParsedParagraph, body_font_size: float) -> bool:
        text = para.text.strip()
        if not text or len(text) > 60:
            return False

        # Explicit heading styles
        style = para.style_name.lower()
        if "heading" in style:
            return True

        # Bold + short text
        if para.font.bold and len(text) < 50:
            # All-caps or title-case short line
            if text.isupper() or self._is_title_case(text):
                return True
            # Known section name
            if text.lower() in KNOWN_SECTION_NAMES:
                return True

        # Larger than body font
        if para.font.size_pt >= body_font_size + self.font_size_threshold:
            if len(text) < 60:
                return True

        # Known section name (case-insensitive)
        if text.lower().rstrip(":") in KNOWN_SECTION_NAMES:
            return True

        return False

    def _estimate_body_font_size(self, paras: list[ParsedParagraph]) -> float:
        """Most common font size across all paragraphs = body size."""
        if not paras:
            return 10.0
        sizes: dict[float, int] = {}
        for p in paras:
            s = p.font.size_pt
            sizes[s] = sizes.get(s, 0) + 1
        return max(sizes, key=sizes.get)

    def _is_title_case(self, text: str) -> bool:
        words = text.split()
        return all(w[0].isupper() for w in words if w and w[0].isalpha())

    def _classify_section_type(self, name: str) -> str:
        normalized = name.lower().strip().rstrip(":")
        return SECTION_TYPE_MAP.get(normalized, "generic")

    # ── Bullet extraction ─────────────────────────────────────────────────────

    @staticmethod
    def extract_bullets(section: DetectedSection) -> list[DetectedBullet]:
        bullets = []
        order = 0
        for para in section.body_paragraphs:
            text = para.text.strip()
            if not text:
                continue
            # Treat any body paragraph as a potential bullet/entry line
            bullets.append(DetectedBullet(text=text, paragraph=para, order_index=order))
            order += 1
        return bullets
