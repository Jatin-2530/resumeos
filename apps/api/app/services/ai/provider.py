"""
AI Provider abstraction layer.

All AI-powered features must go through this interface. This decouples
the business logic from any specific AI vendor and enables future
swapping between Gemini, Claude, OpenAI, etc.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class OptimizedBullet:
    text: str
    rationale: str = ""
    estimated_chars: int = 0


@dataclass
class JDAnalysis:
    title: Optional[str]
    company: Optional[str]
    extracted_keywords: list[str]
    skill_clusters: dict[str, list[str]]
    competencies: list[str]
    action_verbs: list[str]
    role_category: str
    ats_keyword_map: dict[str, float]


@dataclass
class SemanticScore:
    readability: float
    leadership_density: float
    quantified_impact: float
    action_verb_strength: float
    overall: float
    suggestions: list[str]


class AIProvider(ABC):
    """Abstract base class for all AI providers."""

    @abstractmethod
    async def optimize_bullets(
        self,
        bullets: list[str],
        constraints: dict,
        jd_keywords: list[str],
        num_alternatives: int = 3,
        section_name: str = "",
    ) -> list[list[OptimizedBullet]]:
        """
        Generate optimized alternatives for a list of bullets.

        Returns a list (one per input bullet) of lists (alternatives).
        """
        ...

    @abstractmethod
    async def analyze_jd(self, jd_text: str) -> JDAnalysis:
        """Extract structured intelligence from a job description."""
        ...

    @abstractmethod
    async def score_resume_section(
        self,
        bullets: list[str],
        jd_keywords: list[str],
        persona: str = "general",
    ) -> SemanticScore:
        """Score a resume section from a recruiter/ATS perspective."""
        ...

    @abstractmethod
    async def anti_ai_rewrite(self, text: str) -> str:
        """Rewrite AI-sounding text to sound more human/authentic."""
        ...
