"""
JD Analyzer — high-level service for job description intelligence.

Wraps the AI provider's JD analysis with caching and keyword scoring.
"""
from __future__ import annotations

import hashlib
from typing import Optional

from .provider import AIProvider, JDAnalysis


class JDAnalyzerService:
    """
    Analyzes job descriptions for ATS keyword extraction and role classification.

    The analysis is stateless (no DB writes) — persistence is the caller's
    responsibility.
    """

    def __init__(self, ai_provider: AIProvider):
        self._ai = ai_provider
        # In-process cache keyed by text hash
        self._cache: dict[str, JDAnalysis] = {}

    async def analyze(self, jd_text: str) -> JDAnalysis:
        text_hash = hashlib.sha256(jd_text.encode()).hexdigest()[:16]
        if text_hash in self._cache:
            return self._cache[text_hash]

        analysis = await self._ai.analyze_jd(jd_text)
        self._cache[text_hash] = analysis
        return analysis

    def compute_match_score(
        self, resume_text: str, jd_analysis: JDAnalysis
    ) -> dict:
        """
        Compute keyword match score between resume text and JD.
        Returns found keywords, missing keywords, and a coverage score.
        """
        resume_lower = resume_text.lower()
        found: list[str] = []
        missing: list[str] = []

        for keyword in jd_analysis.extracted_keywords:
            if keyword.lower() in resume_lower:
                found.append(keyword)
            else:
                missing.append(keyword)

        total = len(jd_analysis.extracted_keywords)
        coverage = len(found) / total if total > 0 else 0.0

        # Weight by importance
        weighted_score = 0.0
        weight_total = 0.0
        for kw, importance in jd_analysis.ats_keyword_map.items():
            weight_total += importance
            if kw.lower() in resume_lower:
                weighted_score += importance

        weighted_coverage = weighted_score / weight_total if weight_total > 0 else coverage

        return {
            "raw_coverage": round(coverage, 3),
            "weighted_coverage": round(weighted_coverage, 3),
            "found_keywords": found,
            "missing_keywords": missing,
            "found_count": len(found),
            "missing_count": len(missing),
            "total_keywords": total,
        }
