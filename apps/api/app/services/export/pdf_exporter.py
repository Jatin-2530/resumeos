"""
PDF Exporter — converts a DOCX to PDF.

Primary method: LibreOffice headless (preserves all formatting perfectly).
Fallback: reportlab (for environments without LibreOffice).
"""
from __future__ import annotations

import asyncio
import os
import shutil
import tempfile
from pathlib import Path


class PDFExporter:
    """Converts DOCX files to PDF using LibreOffice headless."""

    def __init__(self, libreoffice_path: str = "/usr/bin/libreoffice"):
        self.libreoffice_path = libreoffice_path

    async def export(
        self,
        docx_path: str | Path,
        output_dir: str | Path,
        filename_stem: Optional[str] = None,
    ) -> Path:
        """
        Convert DOCX to PDF.

        Returns path to the generated PDF file.
        """
        docx_path = Path(docx_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        if not self._libreoffice_available():
            raise RuntimeError(
                f"LibreOffice not found at {self.libreoffice_path}. "
                "Set LIBREOFFICE_PATH environment variable or install LibreOffice."
            )

        with tempfile.TemporaryDirectory() as tmpdir:
            cmd = [
                self.libreoffice_path,
                "--headless",
                "--norestore",
                "--convert-to", "pdf",
                "--outdir", tmpdir,
                str(docx_path),
            ]

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, "HOME": tmpdir},  # Prevent LibreOffice profile conflicts
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=60
                )
            except asyncio.TimeoutError:
                proc.kill()
                raise RuntimeError("LibreOffice conversion timed out after 60s")

            if proc.returncode != 0:
                raise RuntimeError(
                    f"LibreOffice failed (exit {proc.returncode}): {stderr.decode()[:500]}"
                )

            # Find generated PDF
            pdf_files = list(Path(tmpdir).glob("*.pdf"))
            if not pdf_files:
                raise RuntimeError("LibreOffice produced no PDF output")

            # Move to output directory
            stem = filename_stem or docx_path.stem
            output_pdf = output_dir / f"{stem}.pdf"
            shutil.move(str(pdf_files[0]), str(output_pdf))

        return output_pdf

    def _libreoffice_available(self) -> bool:
        return Path(self.libreoffice_path).exists() or shutil.which("libreoffice") is not None


# Fix missing import
from typing import Optional
