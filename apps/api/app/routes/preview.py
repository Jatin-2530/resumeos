"""
Preview routes — generate live layout preview data for the editor.
"""
from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from supabase import Client

from ..config import Settings, get_settings
from ..dependencies import get_current_user, get_supabase
from ..services.layout.constraint_engine import LayoutConstraintEngine
from ..services.layout.overflow_detector import FastOverflowDetector

logger = structlog.get_logger()
router = APIRouter(prefix="/preview", tags=["preview"])


class PreviewRequest(BaseModel):
    resume_id: str


class BulletPreviewRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=500)
    resume_id: str
    section_name: str | None = None


# ── Full resume layout preview ────────────────────────────────────────────────

@router.post("/{resume_id}")
async def get_resume_preview(
    resume_id: str,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
):
    """
    Returns layout validation data for the entire resume.
    Used to drive the live preview panel.
    """
    resume_result = (
        supabase.table("resumes")
        .select("dna_schema")
        .eq("id", resume_id)
        .eq("user_id", current_user["id"])
        .single()
        .execute()
    )
    if not resume_result.data:
        raise HTTPException(status_code=404, detail="Resume not found")

    dna_schema = resume_result.data.get("dna_schema")
    if not dna_schema:
        raise HTTPException(status_code=422, detail="Resume has no DNA schema")

    # Fetch current sections and bullets
    sections_result = (
        supabase.table("resume_sections")
        .select("id, name, order_index")
        .eq("resume_id", resume_id)
        .order("order_index")
        .execute()
    )

    sections_with_bullets = []
    for section in (sections_result.data or []):
        bullets_result = (
            supabase.table("resume_bullets")
            .select("id, current_text, order_index")
            .eq("section_id", section["id"])
            .order("order_index")
            .execute()
        )
        sections_with_bullets.append({
            "id": section["id"],
            "name": section["name"],
            "bullets": [
                {"id": b["id"], "text": b["current_text"]}
                for b in (bullets_result.data or [])
            ],
        })

    # Run fast overflow detection
    from ..schemas.dna import DocumentDNA
    dna = DocumentDNA.model_validate(dna_schema)
    detector = FastOverflowDetector(dna)
    report = detector.check_resume(sections_with_bullets)

    # Build per-bullet validation map
    engine = LayoutConstraintEngine(dna)
    bullet_validations = {}
    for section in sections_with_bullets:
        for bullet in section["bullets"]:
            v = engine.validate_bullet(bullet["text"], section["name"])
            bullet_validations[bullet["id"]] = {
                "estimated_lines": v.estimated_lines,
                "max_lines": v.max_lines,
                "overflow": v.overflow,
                "warnings": v.warnings,
            }

    return {
        "resume_id": resume_id,
        "has_overflow": report.has_overflow,
        "overflow_count": len([b for b in report.overflow_bullets if b.validation.overflow]),
        "warning_count": len(report.warnings),
        "sections": sections_with_bullets,
        "bullet_validations": bullet_validations,
        "constraints": engine.get_prompt_constraints(),
    }


# ── Single bullet preview ─────────────────────────────────────────────────────

@router.post("/bullet")
async def preview_bullet(
    payload: BulletPreviewRequest,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
):
    """Real-time constraint check for a single bullet text."""
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
        return {"estimated_lines": 1, "overflow": False, "warnings": []}

    from ..schemas.dna import DocumentDNA
    dna = DocumentDNA.model_validate(dna_schema)
    engine = LayoutConstraintEngine(dna)
    result = engine.validate_bullet(payload.text, payload.section_name)

    return {
        "estimated_lines": result.estimated_lines,
        "max_lines": result.max_lines,
        "overflow": result.overflow,
        "overflow_lines": result.overflow_lines,
        "warnings": result.warnings,
        "char_count": len(payload.text),
        "max_chars_estimate": result.metrics.get("max_chars_estimate", 0),
    }
