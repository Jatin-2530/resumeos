"""
Generation routes — constraint-aware AI bullet optimization.
"""
from __future__ import annotations

import uuid
import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from ..config import Settings, get_settings
from ..dependencies import get_current_user, get_supabase
from ..schemas.ats import (
    GenerateAlternativesRequest,
    GenerateAlternativesOut,
    SelectAlternativeRequest,
)
from ..services.ai.gemini_provider import GeminiProvider
from ..services.ai.orchestrator import AIOrchestrator
from ..services.schema.dna_extractor import DNAExtractor

logger = structlog.get_logger()
router = APIRouter(prefix="/generation", tags=["generation"])

_dna_extractor = DNAExtractor()


def _get_ai_provider(settings: Settings) -> GeminiProvider:
    return GeminiProvider(
        api_key=settings.gemini_api_key,
        flash_model=settings.gemini_flash_model,
        pro_model=settings.gemini_pro_model,
    )


# ── Generate alternatives ──────────────────────────────────────────────────────

@router.post("/alternatives", response_model=GenerateAlternativesOut)
async def generate_alternatives(
    payload: GenerateAlternativesRequest,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
    settings: Settings = Depends(get_settings),
):
    """
    Generate constraint-aware bullet alternatives for a given bullet + JD.
    """
    # Fetch bullet
    bullet_result = (
        supabase.table("resume_bullets")
        .select("*, resume_sections(name, resume_id)")
        .eq("id", payload.bullet_id)
        .single()
        .execute()
    )
    if not bullet_result.data:
        raise HTTPException(status_code=404, detail="Bullet not found")

    bullet = bullet_result.data
    section_name = bullet.get("resume_sections", {}).get("name", "")
    resume_id = bullet.get("resume_sections", {}).get("resume_id")

    # Verify ownership
    if resume_id:
        resume_check = (
            supabase.table("resumes")
            .select("id, dna_schema")
            .eq("id", resume_id)
            .eq("user_id", current_user["id"])
            .single()
            .execute()
        )
        if not resume_check.data:
            raise HTTPException(status_code=403, detail="Access denied")
        dna_schema = resume_check.data.get("dna_schema")
    else:
        raise HTTPException(status_code=400, detail="Bullet has no associated resume")

    # Fetch JD keywords
    jd_result = (
        supabase.table("job_descriptions")
        .select("extracted_keywords, ats_keyword_map")
        .eq("id", payload.jd_id)
        .eq("user_id", current_user["id"])
        .single()
        .execute()
    )
    if not jd_result.data:
        raise HTTPException(status_code=404, detail="Job description not found")

    jd_keywords = jd_result.data.get("extracted_keywords", [])

    # Build orchestrator from DNA
    if not dna_schema:
        raise HTTPException(
            status_code=422,
            detail="Resume has no DNA schema. Re-upload the resume.",
        )

    from ..schemas.dna import DocumentDNA
    try:
        dna = DocumentDNA.model_validate(dna_schema)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid DNA schema: {e}")

    ai_provider = _get_ai_provider(settings)
    orchestrator = AIOrchestrator(ai_provider, dna)

    generation_id = str(uuid.uuid4())
    result = await orchestrator.generate_alternatives(
        generation_id=generation_id,
        bullet_text=bullet["current_text"],
        section_name=section_name,
        jd_keywords=jd_keywords,
        num_alternatives=payload.num_alternatives,
    )

    # Persist generation record
    supabase.table("ai_generations").insert({
        "id": generation_id,
        "bullet_id": payload.bullet_id,
        "jd_id": payload.jd_id,
        "original_text": bullet["current_text"],
        "alternatives": [a.model_dump() for a in result.alternatives],
        "model_used": settings.gemini_flash_model,
        "validation_results": result.constraints,
    }).execute()

    return GenerateAlternativesOut(
        generation_id=generation_id,
        bullet_id=payload.bullet_id,
        original_text=bullet["current_text"],
        alternatives=result.alternatives,
        constraints=result.constraints,
    )


# ── Select alternative ─────────────────────────────────────────────────────────

@router.post("/select")
async def select_alternative(
    payload: SelectAlternativeRequest,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
):
    """Mark a generated alternative as selected and update the bullet text."""
    gen_result = (
        supabase.table("ai_generations")
        .select("*, resume_bullets(resume_id)")
        .eq("id", payload.generation_id)
        .single()
        .execute()
    )
    if not gen_result.data:
        raise HTTPException(status_code=404, detail="Generation not found")

    generation = gen_result.data
    bullet_id = generation["bullet_id"]
    resume_id = generation.get("resume_bullets", {}).get("resume_id")

    # Ownership check
    if resume_id:
        resume_check = (
            supabase.table("resumes")
            .select("id")
            .eq("id", resume_id)
            .eq("user_id", current_user["id"])
            .single()
            .execute()
        )
        if not resume_check.data:
            raise HTTPException(status_code=403, detail="Access denied")

    # Update the selected alternative
    supabase.table("ai_generations").update(
        {"selected_alternative": payload.selected_text}
    ).eq("id", payload.generation_id).execute()

    # Update bullet current text
    supabase.table("resume_bullets").update(
        {"current_text": payload.selected_text}
    ).eq("id", bullet_id).execute()

    return {"status": "updated", "bullet_id": bullet_id, "text": payload.selected_text}


# ── Batch generate for whole resume ───────────────────────────────────────────

@router.post("/batch/{resume_id}")
async def batch_generate(
    resume_id: str,
    jd_id: str,
    num_alternatives: int = 3,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
    settings: Settings = Depends(get_settings),
):
    """
    Kick off generation for ALL unlocked bullets in a resume.
    Returns a list of generation results.
    """
    resume_result = (
        supabase.table("resumes")
        .select("id, dna_schema")
        .eq("id", resume_id)
        .eq("user_id", current_user["id"])
        .single()
        .execute()
    )
    if not resume_result.data:
        raise HTTPException(status_code=404, detail="Resume not found")

    dna_schema = resume_result.data.get("dna_schema")
    if not dna_schema:
        raise HTTPException(status_code=422, detail="Resume missing DNA schema")

    # Load bullets
    bullets_result = (
        supabase.table("resume_bullets")
        .select("id, current_text, resume_sections(name)")
        .eq("resume_id", resume_id)
        .eq("is_locked", False)
        .execute()
    )

    # Load JD
    jd_result = (
        supabase.table("job_descriptions")
        .select("extracted_keywords")
        .eq("id", jd_id)
        .eq("user_id", current_user["id"])
        .single()
        .execute()
    )
    if not jd_result.data:
        raise HTTPException(status_code=404, detail="JD not found")

    jd_keywords = jd_result.data.get("extracted_keywords", [])

    from ..schemas.dna import DocumentDNA
    dna = DocumentDNA.model_validate(dna_schema)
    ai_provider = _get_ai_provider(settings)
    orchestrator = AIOrchestrator(ai_provider, dna)

    results = []
    for bullet in bullets_result.data[:30]:  # Limit to 30 bullets per batch
        gen_id = str(uuid.uuid4())
        section_name = bullet.get("resume_sections", {}).get("name", "")
        result = await orchestrator.generate_alternatives(
            generation_id=gen_id,
            bullet_text=bullet["current_text"],
            section_name=section_name,
            jd_keywords=jd_keywords,
            num_alternatives=num_alternatives,
        )
        results.append({
            "generation_id": gen_id,
            "bullet_id": bullet["id"],
            "alternatives": [a.model_dump() for a in result.alternatives],
        })

    return {"resume_id": resume_id, "generations": results}
