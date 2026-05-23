"""
Gemini AI Provider — implements AIProvider using Google Gemini 2.5.

Model routing:
  - Flash: bullet optimization, ATS scoring, anti-AI (latency-sensitive)
  - Pro: JD analysis, full resume scoring, complex instructions

Prompt engineering principles:
  - Always inject constraint schema so Gemini knows the line budget.
  - Structured output: numbered lists only (easy to parse reliably).
  - Explicit refusal signals so we can detect failures gracefully.
"""
from __future__ import annotations

import json
import re
import asyncio
from typing import Optional

import google.generativeai as genai

from .provider import AIProvider, OptimizedBullet, JDAnalysis, SemanticScore


_BULLET_SYSTEM_PROMPT = """You are an expert resume writer specializing in MBA placement and management consulting resumes.

You generate alternative resume bullet points that:
1. Are ATS-optimized with relevant keywords
2. Begin with a strong, specific action verb
3. Include quantified impact wherever possible
4. Sound authentic — NOT generic AI filler
5. STRICTLY FIT within the formatting constraints provided

FORMATTING IS PARAMOUNT. You MUST NOT produce text that exceeds the line budget.
If you cannot improve a bullet while respecting constraints, return the original.
"""

_JD_SYSTEM_PROMPT = """You are an expert at analyzing job descriptions for ATS optimization and recruiter intelligence.
Extract structured data as valid JSON only. No markdown fences, no explanation."""

_SCORE_SYSTEM_PROMPT = """You are a senior recruiter with 15 years of hiring experience at McKinsey, Goldman Sachs, and Google.
Score resume content objectively. Return valid JSON only."""


class GeminiProvider(AIProvider):
    """
    AI provider backed by Google Gemini 2.5 Flash and Pro.
    """

    def __init__(
        self,
        api_key: str,
        flash_model: str = "gemini-2.5-flash-preview-05-20",
        pro_model: str = "gemini-2.5-pro-preview-05-06",
    ):
        genai.configure(api_key=api_key)
        self._flash = genai.GenerativeModel(
            flash_model,
            system_instruction=_BULLET_SYSTEM_PROMPT,
        )
        self._pro = genai.GenerativeModel(
            pro_model,
            system_instruction=_JD_SYSTEM_PROMPT,
        )
        self._pro_score = genai.GenerativeModel(
            pro_model,
            system_instruction=_SCORE_SYSTEM_PROMPT,
        )

    # ── Bullet optimization ───────────────────────────────────────────────────

    async def optimize_bullets(
        self,
        bullets: list[str],
        constraints: dict,
        jd_keywords: list[str],
        num_alternatives: int = 3,
        section_name: str = "",
    ) -> list[list[OptimizedBullet]]:
        tasks = [
            self._optimize_single_bullet(
                bullet, constraints, jd_keywords, num_alternatives, section_name
            )
            for bullet in bullets
        ]
        return await asyncio.gather(*tasks)

    async def _optimize_single_bullet(
        self,
        bullet: str,
        constraints: dict,
        jd_keywords: list[str],
        num_alternatives: int,
        section_name: str,
    ) -> list[OptimizedBullet]:
        prompt = self._build_bullet_prompt(
            bullet, constraints, jd_keywords, num_alternatives, section_name
        )
        try:
            response = await self._flash.generate_content_async(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=512,
                ),
            )
            return self._parse_bullet_alternatives(response.text, num_alternatives)
        except Exception as exc:
            # Graceful degradation: return original
            return [OptimizedBullet(text=bullet, rationale=f"Generation failed: {exc}")]

    def _build_bullet_prompt(
        self,
        bullet: str,
        constraints: dict,
        keywords: list[str],
        n: int,
        section_name: str,
    ) -> str:
        max_lines = constraints.get("max_lines", 2)
        max_chars = constraints.get("max_chars_per_line", 95)
        font = constraints.get("font_family", "Calibri")
        size = constraints.get("font_size", 10)
        section_hint = f" for the {section_name} section" if section_name else ""

        keywords_str = ", ".join(keywords[:25]) if keywords else "none provided"

        return f"""Generate {n} improved alternatives for this resume bullet{section_hint}.

ORIGINAL BULLET:
{bullet}

HARD CONSTRAINTS (MUST obey — layout preservation is critical):
- Maximum {max_lines} lines when rendered in {font} {size}pt
- Each line holds approximately {max_chars} characters
- Total character budget ≈ {max_chars * max_lines} characters (including spaces)
- Begin with a strong action verb (Led, Drove, Architected, Delivered, etc.)
- NO bullet character prefix — just the text

TARGET KEYWORDS (use the most relevant 2-4):
{keywords_str}

OUTPUT FORMAT — return EXACTLY {n} lines, numbered 1-{n}:
1. [alternative one]
2. [alternative two]
3. [alternative three]

No explanations. No extra text. Just the {n} numbered alternatives."""

    def _parse_bullet_alternatives(
        self, text: str, expected_count: int
    ) -> list[OptimizedBullet]:
        alternatives = []
        lines = text.strip().split("\n")
        for line in lines:
            # Match "1. text", "2. text", etc.
            match = re.match(r"^\d+\.\s+(.+)$", line.strip())
            if match:
                alt_text = match.group(1).strip()
                # Remove leading bullet characters if model adds them
                alt_text = re.sub(r"^[•·\-–—]\s*", "", alt_text)
                if alt_text:
                    alternatives.append(
                        OptimizedBullet(text=alt_text, estimated_chars=len(alt_text))
                    )
        # Pad with empty if we got fewer than expected
        return alternatives[:expected_count] if alternatives else []

    # ── JD analysis ───────────────────────────────────────────────────────────

    async def analyze_jd(self, jd_text: str) -> JDAnalysis:
        prompt = f"""Analyze this job description and return a JSON object with exactly these fields:

{{
  "title": "job title or null",
  "company": "company name or null",
  "extracted_keywords": ["keyword1", "keyword2", ...],
  "skill_clusters": {{
    "technical": ["skill1", "skill2"],
    "leadership": ["skill1"],
    "domain": ["skill1", "skill2"]
  }},
  "competencies": ["competency1", "competency2", ...],
  "action_verbs": ["verb1", "verb2", ...],
  "role_category": "consulting|finance|tech|product|operations|marketing|other",
  "ats_keyword_map": {{"keyword": importance_score_0_to_1, ...}}
}}

Extracted keywords should be the 20-30 most ATS-critical terms.
ats_keyword_map importance: 1.0 = mentioned multiple times / required, 0.5 = preferred, 0.2 = nice-to-have.

JOB DESCRIPTION:
{jd_text[:8000]}

Return ONLY the JSON object. No markdown. No explanation."""

        try:
            response = await self._pro.generate_content_async(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=2048,
                ),
            )
            return self._parse_jd_analysis(response.text)
        except Exception as exc:
            return JDAnalysis(
                title=None,
                company=None,
                extracted_keywords=[],
                skill_clusters={},
                competencies=[],
                action_verbs=[],
                role_category="other",
                ats_keyword_map={},
            )

    def _parse_jd_analysis(self, text: str) -> JDAnalysis:
        # Strip markdown fences if present
        clean = re.sub(r"```(?:json)?\n?", "", text).strip().rstrip("```").strip()
        try:
            data = json.loads(clean)
            return JDAnalysis(
                title=data.get("title"),
                company=data.get("company"),
                extracted_keywords=data.get("extracted_keywords", []),
                skill_clusters=data.get("skill_clusters", {}),
                competencies=data.get("competencies", []),
                action_verbs=data.get("action_verbs", []),
                role_category=data.get("role_category", "other"),
                ats_keyword_map=data.get("ats_keyword_map", {}),
            )
        except json.JSONDecodeError:
            return JDAnalysis(
                title=None, company=None,
                extracted_keywords=[], skill_clusters={},
                competencies=[], action_verbs=[],
                role_category="other", ats_keyword_map={},
            )

    # ── Resume scoring ────────────────────────────────────────────────────────

    async def score_resume_section(
        self,
        bullets: list[str],
        jd_keywords: list[str],
        persona: str = "general",
    ) -> SemanticScore:
        bullets_text = "\n".join(f"- {b}" for b in bullets)
        keywords_text = ", ".join(jd_keywords[:20])

        prompt = f"""As a {persona} recruiter, score these resume bullets from 0-100 on each dimension.

BULLETS:
{bullets_text}

TARGET KEYWORDS: {keywords_text}

Return ONLY this JSON:
{{
  "readability": 0-100,
  "leadership_density": 0-100,
  "quantified_impact": 0-100,
  "action_verb_strength": 0-100,
  "overall": 0-100,
  "suggestions": ["suggestion1", "suggestion2", "suggestion3"]
}}"""

        try:
            response = await self._pro_score.generate_content_async(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=512,
                ),
            )
            clean = re.sub(r"```(?:json)?\n?", "", response.text).strip().rstrip("```")
            data = json.loads(clean)
            return SemanticScore(
                readability=float(data.get("readability", 50)),
                leadership_density=float(data.get("leadership_density", 50)),
                quantified_impact=float(data.get("quantified_impact", 50)),
                action_verb_strength=float(data.get("action_verb_strength", 50)),
                overall=float(data.get("overall", 50)),
                suggestions=data.get("suggestions", []),
            )
        except Exception:
            return SemanticScore(
                readability=50, leadership_density=50,
                quantified_impact=50, action_verb_strength=50,
                overall=50, suggestions=[],
            )

    # ── Anti-AI rewrite ───────────────────────────────────────────────────────

    async def anti_ai_rewrite(self, text: str) -> str:
        prompt = f"""Rewrite this resume bullet to sound more authentic and human.
Remove generic AI phrases like "leveraged", "spearheaded", "utilized", "facilitated".
Keep the same meaning and quantified achievements. Be specific and direct.

ORIGINAL: {text}

Return ONLY the rewritten bullet. No explanation."""

        try:
            response = await self._flash.generate_content_async(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.6,
                    max_output_tokens=200,
                ),
            )
            return response.text.strip()
        except Exception:
            return text
