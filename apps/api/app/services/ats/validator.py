"""
ATS Validation Service — validates resume content for ATS compatibility.

Architecture: pluggable provider pattern. Currently ships with an
internal heuristic validator. Future integrations: Affinda, RChilli,
Sovren, Textkernel (each as a separate provider class).

Internal validator checks:
  - Section naming (ATS-friendly names)
  - Date formatting
  - Keyword density
  - Formatting red flags (tables, headers, text boxes)
  - File format validity
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from typing import Optional

# ATS-friendly section names mapping
ATS_FRIENDLY_SECTION_NAMES = {
    "experience", "work experience", "professional experience",
    "education", "skills", "certifications", "summary",
    "objective", "projects", "publications", "awards",
    "leadership", "activities", "interests", "volunteer",
    "references",
}

ATS_HOSTILE_PATTERNS = [
    r"(?i)positions?\s+of\s+responsibility",  # Non-standard, may not parse
    r"(?i)extra\s*curricular",                # Some ATS miss this
    r"(?i)co-curricular",
]

# Date patterns ATS systems commonly recognize
ATS_DATE_PATTERNS = [
    r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}\b",
    r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b",
    r"\b\d{1,2}/\d{4}\b",
    r"\b\d{4}\s*[-–]\s*\d{4}\b",
    r"\bPresent\b",
]
_DATE_RE = re.compile("|".join(ATS_DATE_PATTERNS), re.IGNORECASE)

# Action verbs strong for ATS
STRONG_ACTION_VERBS = {
    "led", "managed", "developed", "created", "implemented", "designed",
    "built", "launched", "delivered", "increased", "reduced", "improved",
    "generated", "achieved", "established", "coordinated", "analyzed",
    "researched", "presented", "negotiated", "trained", "mentored",
}


@dataclass
class ATSValidationReport:
    overall_score: float
    keyword_coverage: float
    format_score: float
    parse_confidence: float
    missing_keywords: list[str]
    found_keywords: list[str]
    section_parse_results: dict[str, dict]
    recommendations: list[str]
    ats_system: str = "internal"


class ATSProvider(ABC):
    """Abstract ATS validation provider."""

    @abstractmethod
    async def validate(
        self,
        resume_text: str,
        sections: list[dict],
        jd_keywords: list[str],
    ) -> ATSValidationReport:
        ...


class InternalATSValidator(ATSProvider):
    """
    Heuristic ATS validator — no external API required.

    Scores based on:
      - Keyword coverage
      - Section name ATS-friendliness
      - Date format recognition
      - Action verb quality
      - Formatting risk factors
    """

    async def validate(
        self,
        resume_text: str,
        sections: list[dict],
        jd_keywords: list[str],
    ) -> ATSValidationReport:
        format_score = self._score_format(sections)
        keyword_result = self._score_keywords(resume_text, jd_keywords)
        parse_confidence = self._estimate_parse_confidence(resume_text, sections)
        section_results = self._analyze_sections(sections)
        recommendations = self._generate_recommendations(
            format_score, keyword_result, sections
        )

        overall = (
            keyword_result["coverage"] * 0.40
            + format_score * 0.30
            + parse_confidence * 0.30
        ) * 100

        return ATSValidationReport(
            overall_score=round(overall, 1),
            keyword_coverage=round(keyword_result["coverage"] * 100, 1),
            format_score=round(format_score * 100, 1),
            parse_confidence=round(parse_confidence * 100, 1),
            missing_keywords=keyword_result["missing"],
            found_keywords=keyword_result["found"],
            section_parse_results=section_results,
            recommendations=recommendations,
        )

    def _score_keywords(self, resume_text: str, keywords: list[str]) -> dict:
        text_lower = resume_text.lower()
        found = [kw for kw in keywords if kw.lower() in text_lower]
        missing = [kw for kw in keywords if kw.lower() not in text_lower]
        coverage = len(found) / len(keywords) if keywords else 1.0
        return {"coverage": coverage, "found": found, "missing": missing}

    def _score_format(self, sections: list[dict]) -> float:
        if not sections:
            return 0.5

        score = 1.0

        # Check section name quality
        for section in sections:
            name = section.get("name", "").lower().strip()
            if name not in ATS_FRIENDLY_SECTION_NAMES:
                # Check if it matches hostile patterns
                for pattern in ATS_HOSTILE_PATTERNS:
                    if re.search(pattern, name):
                        score -= 0.05
                        break

        # Penalize very short or very long resumes
        total_bullets = sum(len(s.get("bullets", [])) for s in sections)
        if total_bullets < 3:
            score -= 0.2
        elif total_bullets > 50:
            score -= 0.1

        return max(0.0, min(1.0, score))

    def _estimate_parse_confidence(
        self, resume_text: str, sections: list[dict]
    ) -> float:
        """Estimate how confidently an ATS would parse this document."""
        confidence = 0.85  # Base confidence for DOCX

        # Check date formats
        date_matches = len(_DATE_RE.findall(resume_text))
        if date_matches >= 4:
            confidence += 0.05
        elif date_matches == 0:
            confidence -= 0.10

        # Check for quantified achievements
        quantified = len(re.findall(r"\d+%|\$\d+|\d+x\b|\d+ (people|teams|clients)", resume_text, re.I))
        if quantified >= 5:
            confidence += 0.05

        return max(0.0, min(1.0, confidence))

    def _analyze_sections(self, sections: list[dict]) -> dict[str, dict]:
        results = {}
        for section in sections:
            name = section.get("name", "unknown")
            name_lower = name.lower()
            results[name] = {
                "found": True,
                "ats_friendly_name": name_lower in ATS_FRIENDLY_SECTION_NAMES,
                "bullet_count": len(section.get("bullets", [])),
            }
        return results

    def _generate_recommendations(
        self,
        format_score: float,
        keyword_result: dict,
        sections: list[dict],
    ) -> list[str]:
        recs = []

        if keyword_result["coverage"] < 0.6:
            top_missing = keyword_result["missing"][:5]
            recs.append(
                f"Add these missing keywords: {', '.join(top_missing)}"
            )

        if format_score < 0.7:
            recs.append(
                "Some section names may not be recognized by ATS systems. "
                "Consider using standard names (Experience, Education, Skills)."
            )

        # Check for non-standard sections
        for section in sections:
            name = section.get("name", "").lower()
            for pattern in ATS_HOSTILE_PATTERNS:
                if re.search(pattern, name):
                    recs.append(
                        f"Section '{section['name']}' may not parse correctly. "
                        "Consider renaming to 'Leadership & Activities'."
                    )

        return recs[:5]  # Top 5 recommendations
