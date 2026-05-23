"""
Recruiter Simulation Engine — scores resume content from multiple recruiter perspectives.

Personas:
  - consulting: McKinsey/BCG/Bain — leadership, structured thinking, impact at scale
  - finance: Goldman/JPMorgan — quantified performance, technical precision
  - startup: Series A/B — bias to action, ownership, scrappiness
  - pm: Product — user thinking, cross-functional influence, shipping
  - hr: Generic HR — clarity, structure, completeness
  - analytics: Data/DS — technical depth, tool familiarity, insight generation
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from ..ai.provider import AIProvider, SemanticScore


@dataclass
class RecruiterScore:
    persona: str
    readability_score: float
    leadership_density: float
    quantified_impact: float
    scan_efficiency: float
    semantic_strength: float
    clutter_score: float  # Lower is better; inverted for display
    overall_score: float
    recommendations: list[str] = field(default_factory=list)


# Per-persona scoring weights
PERSONA_WEIGHTS = {
    "consulting": {
        "readability": 0.15,
        "leadership_density": 0.25,
        "quantified_impact": 0.30,
        "scan_efficiency": 0.15,
        "semantic_strength": 0.15,
    },
    "finance": {
        "readability": 0.10,
        "leadership_density": 0.15,
        "quantified_impact": 0.40,
        "scan_efficiency": 0.15,
        "semantic_strength": 0.20,
    },
    "startup": {
        "readability": 0.20,
        "leadership_density": 0.20,
        "quantified_impact": 0.25,
        "scan_efficiency": 0.20,
        "semantic_strength": 0.15,
    },
    "pm": {
        "readability": 0.20,
        "leadership_density": 0.20,
        "quantified_impact": 0.25,
        "scan_efficiency": 0.15,
        "semantic_strength": 0.20,
    },
    "hr": {
        "readability": 0.30,
        "leadership_density": 0.15,
        "quantified_impact": 0.20,
        "scan_efficiency": 0.20,
        "semantic_strength": 0.15,
    },
    "analytics": {
        "readability": 0.10,
        "leadership_density": 0.10,
        "quantified_impact": 0.30,
        "scan_efficiency": 0.15,
        "semantic_strength": 0.35,
    },
}


class RecruiterSimulator:
    """
    Generates recruiter scores for resume sections.

    Heuristic scoring for fast feedback; can optionally delegate deep
    scoring to the AI provider.
    """

    def __init__(self, ai_provider: Optional[AIProvider] = None):
        self._ai = ai_provider

    async def score(
        self,
        sections: list[dict],
        jd_keywords: list[str],
        personas: Optional[list[str]] = None,
    ) -> list[RecruiterScore]:
        if personas is None:
            personas = ["consulting", "hr"]

        all_bullets = []
        for section in sections:
            all_bullets.extend(section.get("bullets", []))

        scores = []
        for persona in personas:
            if self._ai and len(all_bullets) > 0:
                try:
                    ai_score = await self._ai.score_resume_section(
                        bullets=all_bullets[:20],
                        jd_keywords=jd_keywords,
                        persona=persona,
                    )
                    score = self._ai_score_to_recruiter_score(ai_score, persona, all_bullets)
                except Exception:
                    score = self._heuristic_score(all_bullets, jd_keywords, persona)
            else:
                score = self._heuristic_score(all_bullets, jd_keywords, persona)
            scores.append(score)

        return scores

    def _ai_score_to_recruiter_score(
        self,
        ai_score: SemanticScore,
        persona: str,
        bullets: list[str],
    ) -> RecruiterScore:
        clutter = self._measure_clutter(bullets)
        scan_efficiency = self._measure_scan_efficiency(bullets)
        weights = PERSONA_WEIGHTS.get(persona, PERSONA_WEIGHTS["hr"])

        raw_scores = {
            "readability": ai_score.readability,
            "leadership_density": ai_score.leadership_density,
            "quantified_impact": ai_score.quantified_impact,
            "scan_efficiency": scan_efficiency,
            "semantic_strength": ai_score.action_verb_strength,
        }
        overall = sum(raw_scores[k] * weights[k] for k in weights)

        return RecruiterScore(
            persona=persona,
            readability_score=ai_score.readability,
            leadership_density=ai_score.leadership_density,
            quantified_impact=ai_score.quantified_impact,
            scan_efficiency=scan_efficiency,
            semantic_strength=ai_score.action_verb_strength,
            clutter_score=clutter,
            overall_score=round(overall, 1),
            recommendations=ai_score.suggestions,
        )

    def _heuristic_score(
        self,
        bullets: list[str],
        jd_keywords: list[str],
        persona: str,
    ) -> RecruiterScore:
        if not bullets:
            return RecruiterScore(
                persona=persona,
                readability_score=50, leadership_density=50,
                quantified_impact=50, scan_efficiency=50,
                semantic_strength=50, clutter_score=20,
                overall_score=50,
            )

        full_text = " ".join(bullets)

        quantified = self._measure_quantified_impact(full_text)
        leadership = self._measure_leadership_density(full_text)
        readability = self._measure_readability(bullets)
        scan_eff = self._measure_scan_efficiency(bullets)
        semantic = self._measure_semantic_strength(bullets, jd_keywords)
        clutter = self._measure_clutter(bullets)

        weights = PERSONA_WEIGHTS.get(persona, PERSONA_WEIGHTS["hr"])
        raw = {
            "readability": readability,
            "leadership_density": leadership,
            "quantified_impact": quantified,
            "scan_efficiency": scan_eff,
            "semantic_strength": semantic,
        }
        overall = sum(raw[k] * weights[k] for k in weights)

        recs = self._generate_recommendations(quantified, leadership, semantic, persona)

        return RecruiterScore(
            persona=persona,
            readability_score=round(readability, 1),
            leadership_density=round(leadership, 1),
            quantified_impact=round(quantified, 1),
            scan_efficiency=round(scan_eff, 1),
            semantic_strength=round(semantic, 1),
            clutter_score=round(clutter, 1),
            overall_score=round(overall, 1),
            recommendations=recs,
        )

    # ── Heuristic measurements ────────────────────────────────────────────────

    def _measure_quantified_impact(self, text: str) -> float:
        matches = re.findall(
            r"\d+%|\$[\d,.]+[KkMmBb]?|\d+[xX]\b|\d+\s*(people|clients|users|teams|projects)",
            text,
            re.I,
        )
        count = len(matches)
        score = min(100, 40 + count * 15)
        return score

    def _measure_leadership_density(self, text: str) -> float:
        leadership_terms = re.findall(
            r"\b(led|managed|mentored|coached|directed|oversee|headed|supervised|"
            r"owned|championed|coordinated|spearheaded|team|cross-functional)\b",
            text,
            re.I,
        )
        score = min(100, 30 + len(leadership_terms) * 12)
        return score

    def _measure_readability(self, bullets: list[str]) -> float:
        if not bullets:
            return 50
        avg_length = sum(len(b) for b in bullets) / len(bullets)
        # Optimal bullet length: 80-160 chars
        if 80 <= avg_length <= 160:
            return 85
        elif avg_length < 50:
            return 55
        elif avg_length > 200:
            return 60
        return 75

    def _measure_scan_efficiency(self, bullets: list[str]) -> float:
        if not bullets:
            return 50
        # Bullets starting with strong verbs score higher
        strong_start = sum(
            1 for b in bullets
            if b.strip() and re.match(r"^[A-Z][a-z]+ed?\b", b.strip())
        )
        ratio = strong_start / len(bullets)
        return round(50 + ratio * 50, 1)

    def _measure_semantic_strength(
        self, bullets: list[str], jd_keywords: list[str]
    ) -> float:
        if not bullets:
            return 50
        full_text = " ".join(bullets).lower()
        if not jd_keywords:
            return 65
        hits = sum(1 for kw in jd_keywords if kw.lower() in full_text)
        coverage = hits / len(jd_keywords)
        return round(50 + coverage * 50, 1)

    def _measure_clutter(self, bullets: list[str]) -> float:
        """Lower clutter score is better. Returns 0-100 where 0 = clean."""
        if not bullets:
            return 0
        total_chars = sum(len(b) for b in bullets)
        avg = total_chars / len(bullets)
        # Very long bullets = clutter
        if avg > 200:
            return 60
        elif avg > 160:
            return 30
        return 10

    def _generate_recommendations(
        self, quantified: float, leadership: float, semantic: float, persona: str
    ) -> list[str]:
        recs = []
        if quantified < 60:
            recs.append("Add more quantified metrics (%, $, counts) to demonstrate impact")
        if leadership < 50 and persona in ("consulting", "finance"):
            recs.append("Strengthen leadership signals — mention team sizes and scope")
        if semantic < 60:
            recs.append("Incorporate more keywords from the job description")
        return recs
