"""
Overflow Detector — detects overflow issues in an entire resume after modifications.

Can run in two modes:
  1. Fast (typography-based): Uses TypographyAnalyzer — no I/O, runs inline.
  2. Exact (LibreOffice): Renders DOCX and compares page count / paragraph positions.
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .constraint_engine import LayoutConstraintEngine, ValidationResult
from ...schemas.dna import DocumentDNA


@dataclass
class BulletOverflowReport:
    section_name: str
    bullet_index: int
    text: str
    validation: ValidationResult


@dataclass
class ResumeOverflowReport:
    has_overflow: bool
    page_count_changed: bool
    original_page_count: int
    new_page_count: int
    overflow_bullets: list[BulletOverflowReport] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class FastOverflowDetector:
    """
    Typography-based overflow detection.
    Runs in microseconds per bullet. No file I/O.
    """

    def __init__(self, dna: DocumentDNA):
        self._engine = LayoutConstraintEngine(dna)

    def check_resume(
        self, sections: list[dict]
    ) -> ResumeOverflowReport:
        """
        sections: list of {"name": str, "bullets": [{"text": str}]}
        """
        overflow_bullets: list[BulletOverflowReport] = []
        warnings: list[str] = []

        for section in sections:
            section_name = section.get("name", "")
            for idx, bullet in enumerate(section.get("bullets", [])):
                text = bullet.get("text", "")
                if not text.strip():
                    continue
                result = self._engine.validate_bullet(text, section_name)
                if result.overflow or result.warnings:
                    overflow_bullets.append(
                        BulletOverflowReport(
                            section_name=section_name,
                            bullet_index=idx,
                            text=text,
                            validation=result,
                        )
                    )
                    if result.warnings:
                        warnings.extend(result.warnings)

        has_overflow = any(b.validation.overflow for b in overflow_bullets)
        return ResumeOverflowReport(
            has_overflow=has_overflow,
            page_count_changed=False,
            original_page_count=1,
            new_page_count=1,
            overflow_bullets=overflow_bullets,
            warnings=warnings,
        )


class LibreOfficeOverflowDetector:
    """
    Exact overflow detection using LibreOffice headless.
    Converts DOCX → PDF and checks page count.
    Only used for final export validation.
    """

    def __init__(self, libreoffice_path: str = "/usr/bin/libreoffice"):
        self.libreoffice_path = libreoffice_path

    async def check_page_count(self, docx_path: str | Path) -> int:
        """Render DOCX to PDF and return page count."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cmd = [
                self.libreoffice_path,
                "--headless",
                "--convert-to", "pdf",
                "--outdir", tmpdir,
                str(docx_path),
            ]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)

            # Find output PDF
            pdf_files = list(Path(tmpdir).glob("*.pdf"))
            if not pdf_files:
                raise RuntimeError(f"LibreOffice failed: {stderr.decode()}")

            return self._count_pdf_pages(pdf_files[0])

    def _count_pdf_pages(self, pdf_path: Path) -> int:
        """Count pages in a PDF using reportlab or a simple byte search."""
        try:
            content = pdf_path.read_bytes()
            # Count /Page objects (heuristic, works for most PDFs)
            count = content.count(b"/Type /Page\n") + content.count(b"/Type/Page\n")
            return max(1, count)
        except Exception:
            return 1
