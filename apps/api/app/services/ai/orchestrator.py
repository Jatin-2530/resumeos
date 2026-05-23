"""
AI Orchestrator — coordinates constraint-aware bullet generation.

This is the heart of ResumeOS's core value proposition:
generate semantically optimized bullets that NEVER break the layout.

Pipeline:
  1. Get constraints for the section.
  2. Ask Gemini for N alternatives.
  3. Validate each alternative against layout constraints.
  4. Re-request if all fail (with tighter char budget).
  5. Return ranked, validated alternatives.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Optional

from .provider import AIProvider, OptimizedBullet
from ..layout.constraint_engine import LayoutConstraintEngine
from ...schemas.dna import DocumentDNA
from ...schemas.ats import GenerationAlternative


@dataclass
class OrchestrationResult:
    generation_id: str
    bullet_text: str
    section_name: str
    alternatives: list[GenerationAlternative]
    constraints: dict
    all_overflowed: bool = False


class AIOrchestrator:
    """
    Constraint-aware AI generation pipeline.

    Guarantees: returned alternatives are validated against layout constraints.
    Alternatives that overflow are flagged (not silently dropped, so user can decide).
    """

    MAX_RETRIES = 2
    RETRY_CHAR_PENALTY = 10  # Reduce char budget by this on retry

    def __init__(self, ai_provider: AIProvider, dna: DocumentDNA):
        self._ai = ai_provider
        self._constraint_engine = LayoutConstraintEngine(dna)

    async def generate_alternatives(
        self,
        generation_id: str,
        bullet_text: str,
        section_name: str,
        jd_keywords: list[str],
        num_alternatives: int = 3,
    ) -> OrchestrationResult:
        constraints = self._constraint_engine.get_prompt_constraints(section_name)

        # First pass
        alternatives_raw = await self._ai.optimize_bullets(
            bullets=[bullet_text],
            constraints=constraints,
            jd_keywords=jd_keywords,
            num_alternatives=num_alternatives,
            section_name=section_name,
        )
        bullet_alternatives = alternatives_raw[0] if alternatives_raw else []

        validated = self._validate_and_rank(
            bullet_alternatives, section_name
        )

        # Retry if all overflowed with tighter budget
        all_overflowed = all(a.overflow_warning for a in validated)
        if all_overflowed and len(validated) > 0:
            tighter = {**constraints}
            tighter["max_chars_per_line"] = max(
                40, constraints["max_chars_per_line"] - self.RETRY_CHAR_PENALTY
            )
            retry_raw = await self._ai.optimize_bullets(
                bullets=[bullet_text],
                constraints=tighter,
                jd_keywords=jd_keywords,
                num_alternatives=num_alternatives,
                section_name=section_name,
            )
            retry_alternatives = retry_raw[0] if retry_raw else []
            retry_validated = self._validate_and_rank(retry_alternatives, section_name)
            # Use retry if it produced valid results
            if any(not a.overflow_warning for a in retry_validated):
                validated = retry_validated
                all_overflowed = False

        return OrchestrationResult(
            generation_id=generation_id,
            bullet_text=bullet_text,
            section_name=section_name,
            alternatives=validated,
            constraints=constraints,
            all_overflowed=all_overflowed,
        )

    def _validate_and_rank(
        self,
        alternatives: list[OptimizedBullet],
        section_name: str,
    ) -> list[GenerationAlternative]:
        results = []
        for alt in alternatives:
            if not alt.text:
                continue
            validation = self._constraint_engine.validate_bullet(
                alt.text, section_name
            )
            # Compute a rough ATS score based on char length and structure
            ats_score = self._estimate_ats_score(alt.text)
            results.append(
                GenerationAlternative(
                    text=alt.text,
                    estimated_lines=validation.estimated_lines,
                    ats_score=ats_score,
                    overflow_warning=validation.overflow,
                )
            )

        # Sort: valid first, then by ATS score descending
        results.sort(key=lambda r: (r.overflow_warning, -r.ats_score))
        return results

    def _estimate_ats_score(self, text: str) -> float:
        """
        Rough ATS signal score based on structural properties.
        Full scoring comes from the ATS validator service.
        """
        score = 50.0

        # Starts with strong verb
        first_word = text.split()[0].lower() if text else ""
        strong_verbs = {
            "led", "drove", "built", "designed", "launched", "delivered",
            "managed", "created", "developed", "implemented", "increased",
            "reduced", "improved", "generated", "negotiated", "architected",
            "scaled", "transformed", "optimized", "established",
        }
        if first_word in strong_verbs:
            score += 15

        # Contains quantification
        import re
        if re.search(r"\d+[%$xX]?|\$[\d,]+|[0-9]+\s*(percent|million|billion|k\b)", text, re.I):
            score += 20

        # Length in range (not too short, not too long)
        length = len(text)
        if 60 <= length <= 180:
            score += 10
        elif length < 40:
            score -= 15

        return min(100.0, max(0.0, score))
