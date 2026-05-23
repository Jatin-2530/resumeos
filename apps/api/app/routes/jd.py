"""
Job Description routes — upload and analyze job descriptions.
"""
from __future__ import annotations

import uuid
import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from supabase import Client

from ..config import Settings, get_settings
from ..dependencies import get_current_user, get_supabase
from ..services.ai.gemini_provider import GeminiProvider
from ..services.ai.jd_analyzer import JDAnalyzerService

logger = structlog.get_logger()
router = APIRouter(prefix="/jd", tags=["job-descriptions"])


class JDUploadRequest(BaseModel):
    text: str = Field(..., min_length=50, max_length=20000)
    title: str | None = None
    company: str | None = None


class JDMatchRequest(BaseModel):
    resume_id: str
    jd_id: str


# ── Upload JD ──────────────────────────────────────────────────────────────────

@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_jd(
    payload: JDUploadRequest,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
    settings: Settings = Depends(get_settings),
):
    """Upload and analyze a job description."""
    ai_provider = GeminiProvider(
        api_key=settings.gemini_api_key,
        flash_model=settings.gemini_flash_model,
        pro_model=settings.gemini_pro_model,
    )
    analyzer = JDAnalyzerService(ai_provider)

    analysis = await analyzer.analyze(payload.text)

    jd_id = str(uuid.uuid4())
    record = {
        "id": jd_id,
        "user_id": current_user["id"],
        "title": payload.title or analysis.title,
        "company": payload.company or analysis.company,
        "raw_text": payload.text,
        "extracted_keywords": analysis.extracted_keywords,
        "skill_clusters": analysis.skill_clusters,
        "competencies": analysis.competencies,
        "action_verbs": analysis.action_verbs,
        "role_category": analysis.role_category,
        "ats_keyword_map": analysis.ats_keyword_map,
    }

    supabase.table("job_descriptions").insert(record).execute()

    logger.info(
        "JD uploaded",
        jd_id=jd_id,
        keywords=len(analysis.extracted_keywords),
        role=analysis.role_category,
    )

    return {
        "id": jd_id,
        "title": record["title"],
        "company": record["company"],
        "role_category": analysis.role_category,
        "keywords_count": len(analysis.extracted_keywords),
        "extracted_keywords": analysis.extracted_keywords,
        "skill_clusters": analysis.skill_clusters,
        "ats_keyword_map": analysis.ats_keyword_map,
    }


# ── List JDs ───────────────────────────────────────────────────────────────────

@router.get("")
async def list_jds(
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
):
    result = (
        supabase.table("job_descriptions")
        .select("id, title, company, role_category, created_at")
        .eq("user_id", current_user["id"])
        .order("created_at", desc=True)
        .limit(20)
        .execute()
    )
    return result.data


# ── Get JD ─────────────────────────────────────────────────────────────────────

@router.get("/{jd_id}")
async def get_jd(
    jd_id: str,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
):
    result = (
        supabase.table("job_descriptions")
        .select("*")
        .eq("id", jd_id)
        .eq("user_id", current_user["id"])
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="JD not found")
    return result.data


# ── Match score ────────────────────────────────────────────────────────────────

@router.post("/match-score")
async def compute_match_score(
    payload: JDMatchRequest,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
    settings: Settings = Depends(get_settings),
):
    """Compute keyword match score between a resume and a JD."""
    resume_result = (
        supabase.table("resume_bullets")
        .select("current_text")
        .eq("resume_id", payload.resume_id)
        .execute()
    )
    jd_result = (
        supabase.table("job_descriptions")
        .select("extracted_keywords, ats_keyword_map")
        .eq("id", payload.jd_id)
        .eq("user_id", current_user["id"])
        .single()
        .execute()
    )
    if not jd_result.data:
        raise HTTPException(status_code=404, detail="JD not found")

    resume_text = " ".join(b["current_text"] for b in (resume_result.data or []))
    from ..services.ai.provider import JDAnalysis
    analysis = JDAnalysis(
        title=None, company=None,
        extracted_keywords=jd_result.data.get("extracted_keywords", []),
        skill_clusters={}, competencies=[], action_verbs=[],
        role_category="", ats_keyword_map=jd_result.data.get("ats_keyword_map", {}),
    )

    ai_provider = GeminiProvider(api_key=settings.gemini_api_key)
    analyzer = JDAnalyzerService(ai_provider)
    match_score = analyzer.compute_match_score(resume_text, analysis)

    return {"resume_id": payload.resume_id, "jd_id": payload.jd_id, **match_score}
