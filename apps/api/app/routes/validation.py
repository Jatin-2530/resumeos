"""
Validation routes — layout and ATS validation.
"""
from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from supabase import Client

from ..config import Settings, get_settings
from ..dependencies import get_current_user, get_supabase
from ..services.ats.validator import InternalATSValidator
from ..services.recruiter.simulator import RecruiterSimulator
from ..services.layout.constraint_engine import LayoutConstraintEngine

logger = structlog.get_logger()
router = APIRouter(prefix="/validation", tags=["validation"])

_ats_validator = InternalATSValidator()


class ValidateBulletRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=500)
    resume_id: str
    section_name: str | None = None


class ValidateResumeRequest(BaseModel):
    resume_id: str
    jd_id: str | None = None


# ── Validate single bullet ────────────────────────────────────────────────────

@router.post("/bullet")
async def validate_bullet(
    payload: ValidateBulletRequest,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
):
    """Check if a bullet text fits within layout constraints."""
    resume_result = (
        supabase.table("resumes")
        .select("dna_schema")
        .eq("id", payload.resume_id)
        .eq("user_id", current_user["id"])
        .single()
        .execute()
    )
    if not resume_result.data:
        raise HTTPException(status_code=404, detail="Resume not found")

    dna_schema = resume_result.data.get("dna_schema")
    if not dna_schema:
        raise HTTPException(status_code=422, detail="Resume has no DNA schema")

    from ..schemas.dna import DocumentDNA
    dna = DocumentDNA.model_validate(dna_schema)
    engine = LayoutConstraintEngine(dna)
    result = engine.validate_bullet(payload.text, payload.section_name)

    return {
        "is_valid": result.is_valid,
        "estimated_lines": result.estimated_lines,
        "max_lines": result.max_lines,
        "overflow": result.overflow,
        "overflow_lines": result.overflow_lines,
        "warnings": result.warnings,
        "metrics": result.metrics,
    }


# ── Full resume ATS validation ────────────────────────────────────────────────

@router.post("/ats")
async def validate_ats(
    payload: ValidateResumeRequest,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
    settings: Settings = Depends(get_settings),
):
    """Run ATS validation on a resume against an optional JD."""
    if not settings.enable_ats_validation:
        raise HTTPException(status_code=503, detail="ATS validation is disabled")

    # Fetch all bullets
    bullets_result = (
        supabase.table("resume_bullets")
        .select("current_text, resume_sections(name)")
        .eq("resume_id", payload.resume_id)
        .execute()
    )
    # Fetch sections
    sections_result = (
        supabase.table("resume_sections")
        .select("name, section_type")
        .eq("resume_id", payload.resume_id)
        .order("order_index")
        .execute()
    )

    resume_text = " ".join(b["current_text"] for b in (bullets_result.data or []))
    sections = sections_result.data or []

    # Build sections with bullets
    sections_with_bullets = []
    for s in sections:
        s_bullets = [
            b["current_text"]
            for b in (bullets_result.data or [])
            if b.get("resume_sections", {}).get("name") == s["name"]
        ]
        sections_with_bullets.append({"name": s["name"], "bullets": s_bullets})

    jd_keywords = []
    if payload.jd_id:
        jd_result = (
            supabase.table("job_descriptions")
            .select("extracted_keywords")
            .eq("id", payload.jd_id)
            .eq("user_id", current_user["id"])
            .single()
            .execute()
        )
        if jd_result.data:
            jd_keywords = jd_result.data.get("extracted_keywords", [])

    report = await _ats_validator.validate(resume_text, sections_with_bullets, jd_keywords)

    # Persist ATS report
    import uuid
    report_id = str(uuid.uuid4())
    supabase.table("ats_reports").insert({
        "id": report_id,
        "resume_id": payload.resume_id,
        "jd_id": payload.jd_id,
        "overall_score": report.overall_score,
        "keyword_coverage": report.keyword_coverage,
        "format_score": report.format_score,
        "parse_confidence": report.parse_confidence,
        "missing_keywords": report.missing_keywords,
        "found_keywords": report.found_keywords,
        "section_parse_results": report.section_parse_results,
        "recommendations": report.recommendations,
    }).execute()

    return {
        "report_id": report_id,
        "overall_score": report.overall_score,
        "keyword_coverage": report.keyword_coverage,
        "format_score": report.format_score,
        "parse_confidence": report.parse_confidence,
        "missing_keywords": report.missing_keywords,
        "found_keywords": report.found_keywords,
        "recommendations": report.recommendations,
    }


# ── Recruiter simulation ───────────────────────────────────────────────────────

@router.post("/recruiter")
async def simulate_recruiter(
    payload: ValidateResumeRequest,
    personas: list[str] = None,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
    settings: Settings = Depends(get_settings),
):
    """Score the resume from multiple recruiter perspectives."""
    if not settings.enable_recruiter_simulation:
        raise HTTPException(status_code=503, detail="Recruiter simulation is disabled")

    bullets_result = (
        supabase.table("resume_bullets")
        .select("current_text, resume_sections(name)")
        .eq("resume_id", payload.resume_id)
        .execute()
    )

    sections_map: dict[str, list[str]] = {}
    for b in (bullets_result.data or []):
        name = b.get("resume_sections", {}).get("name", "General")
        sections_map.setdefault(name, []).append(b["current_text"])

    sections = [{"name": k, "bullets": v} for k, v in sections_map.items()]

    jd_keywords = []
    if payload.jd_id:
        jd_result = (
            supabase.table("job_descriptions")
            .select("extracted_keywords")
            .eq("id", payload.jd_id)
            .single()
            .execute()
        )
        if jd_result.data:
            jd_keywords = jd_result.data.get("extracted_keywords", [])

    from ..services.ai.gemini_provider import GeminiProvider
    ai_provider = GeminiProvider(api_key=settings.gemini_api_key)
    simulator = RecruiterSimulator(ai_provider=ai_provider)
    scores = await simulator.score(
        sections=sections,
        jd_keywords=jd_keywords,
        personas=personas or ["consulting", "hr"],
    )

    return [
        {
            "persona": s.persona,
            "overall_score": s.overall_score,
            "readability_score": s.readability_score,
            "leadership_density": s.leadership_density,
            "quantified_impact": s.quantified_impact,
            "scan_efficiency": s.scan_efficiency,
            "semantic_strength": s.semantic_strength,
            "clutter_score": s.clutter_score,
            "recommendations": s.recommendations,
        }
        for s in scores
    ]
