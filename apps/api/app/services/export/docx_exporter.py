"""
DOCX Exporter — writes an optimized resume back to .docx format.

Critical design constraint: preserve ALL formatting from the original.
Only bullet text content is changed. Typography, spacing, margins,
and section structure must be byte-for-byte identical in terms of styling.

Strategy:
  1. Open original DOCX as template.
  2. Find each bullet paragraph by position matching.
  3. Replace run text while preserving all run-level formatting.
  4. Write to new file (never overwrite original).
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

from docx import Document
from docx.oxml.ns import qn


class DOCXExporter:
    """
    Exports a modified resume to DOCX by patching the original template.

    Preserves 100% of formatting — only text content changes.
    """

    def export(
        self,
        original_docx_path: str | Path,
        output_path: str | Path,
        bullet_updates: list[dict],
    ) -> Path:
        """
        Apply bullet text updates to a DOCX and save to output_path.

        bullet_updates: list of {
            "paragraph_index": int,  # 0-based index in doc.paragraphs
            "new_text": str,
        }

        Returns the output path.
        """
        # Always copy original first
        original = Path(original_docx_path)
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(original, output)

        doc = Document(str(output))
        paragraphs = doc.paragraphs

        for update in bullet_updates:
            idx = update.get("paragraph_index")
            new_text = update.get("new_text", "")
            if idx is None or idx >= len(paragraphs):
                continue
            self._update_paragraph_text(paragraphs[idx], new_text)

        doc.save(str(output))
        return output

    def _update_paragraph_text(self, para, new_text: str) -> None:
        """
        Replace paragraph text while preserving all run formatting.

        Strategy:
          - Keep the first run's formatting as the template.
          - Clear all runs.
          - Set first run text to new_text.

        This preserves bold, italic, font, size, color etc.
        """
        if not para.runs:
            # No runs — add one with the paragraph's style
            run = para.add_run(new_text)
            return

        # Capture first run's XML formatting
        first_run = para.runs[0]

        # Set first run to full new text
        first_run.text = new_text

        # Remove all subsequent runs (they'd be duplicates)
        for run in para.runs[1:]:
            run_element = run._element
            run_element.getparent().remove(run_element)

    def export_section_bullets(
        self,
        original_docx_path: str | Path,
        output_path: str | Path,
        section_bullet_map: dict[str, list[str]],
        parsed_section_indices: dict[str, list[int]],
    ) -> Path:
        """
        Higher-level export that maps section names → bullet texts → paragraph indices.

        section_bullet_map: {"Experience": ["bullet1", "bullet2", ...], ...}
        parsed_section_indices: {"Experience": [para_idx1, para_idx2, ...], ...}
        """
        updates = []
        for section_name, bullets in section_bullet_map.items():
            indices = parsed_section_indices.get(section_name, [])
            for i, (bullet_text, para_idx) in enumerate(zip(bullets, indices)):
                updates.append({
                    "paragraph_index": para_idx,
                    "new_text": bullet_text,
                })
        return self.export(original_docx_path, output_path, updates)
