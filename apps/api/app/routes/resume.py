"""
Resume routes — upload, parse, retrieve, manage resumes.
"""
from __future__ import annotations

import os
import uuid
import tempfile
from pathlib import Path
from typing import Optional

import aiofiles
import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from supabase import Client

try:
    import magic
    _MAGIC_AVAILABLE = True
except ImportError:
    _MAGIC_AVAILABLE = False

from ..config import Settings, get_settings
from ..dependencies import get_current_user, get_supabase
from ..schemas.resume import ResumeOut, ResumeListItem, UpdateBulletRequest, LockBulletRequest
from ..services.docx.parser import DOCXParser
from ..services.docx.section_detector import SectionDetector
from ..services.schema.dna_extractor import DNAExtractor

logger = structlog.get_logger()
router = APIRouter(prefix="/resumes", tags=["resumes"])

_dna_extractor = DNAExtractor()
_section_detector = SectionDetector()
_docx_parser = DOCXParser()

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
PDF_MIME = "application/pdf"


def _detect_mime(content: bytes) -> str:
    if _MAGIC_AVAILABLE:
        return magic.from_buffer(content[:2048], mime=True)
    # Fallback: check file signatures
    if content[:4] == b'PK\x03\x04':
        return DOCX_MIME
    if content[:4] == b'%PDF':
        return PDF_MIME
    return "application/octet-stream"


# ── Upload ─────────────────────────────────────────────────────────────────────

@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: UploadFile = File(...),
    title: str = Form(default=""),
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
    settings: Settings = Depends(get_settings),
):
    """
    Upload a DOCX or PDF resume.
    Returns the resume record with extracted schema.
    """
    content = await file.read()
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds {settings.max_upload_size_mb}MB limit",
        )

    detected_mime = _detect_mime(content)
    if detected_mime not in settings.allowed_mime_types:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type: {detected_mime}",
        )

    file_type = "docx" if "wordprocessingml" in detected_mime else "pdf"
    resume_id = str(uuid.uuid4())
    user_id = current_user["id"]
    file_title = title or Path(file.filename or "resume").stem

    storage_path = f"resumes/original/{user_id}/{resume_id}.{file_type}"
    try:
        supabase.storage.from_(settings.supabase_storage_bucket).upload(
            path=storage_path,
            file=content,
            file_options={"content-type": detected_mime},
        )
    except Exception as e:
        logger.warning("Storage upload failed", error=str(e))

    dna_schema = None
    sections_data = []

    if file_type == "docx":
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            dna = _dna_extractor.extract(tmp_path)
            dna_schema = dna.model_dump()

            doc = _docx_parser.parse(tmp_path)
            detected = _section_detector.detect(doc)
            sections_data = [
                {
                    "id": str(uuid.uuid4()),
                    "name": s.name,
                    "section_type": s.section_type,
                    "order_index": s.order_index,
                    "bullets": [
                        {
                            "id": str(uuid.uuid4()),
                            "text": b.text,
                            "order_index": b.order_index,
                        }
                        for b in _section_detector.extract_bullets(s)
                    ],
                }
                for s in detected
            ]
        except Exception as e:
            logger.warning("DNA extraction failed", error=str(e))
        finally:
            os.unlink(tmp_path)

    resume_record = {
        "id": resume_id,
        "user_id": user_id,
        "title": file_title,
        "original_file_path": storage_path,
        "original_file_type": file_type,
        "original_file_size": len(content),
        "status": "ready" if dna_schema else "processing",
        "dna_schema": dna_schema,
    }
    supabase.table("resumes").insert(resume_record).execute()

    for section in sections_data:
        section_id = section["id"]
        supabase.table("resume_sections").insert({
            "id": section_id,
            "resume_id": resume_id,
            "name": section["name"],
            "section_type": section["section_type"],
            "order_index": section["order_index"],
        }).execute()

        for bullet in section["bullets"]:
            supabase.table("resume_bullets").insert({
                "id": bullet["id"],
                "section_id": section_id,
                "resume_id": resume_id,
                "order_index": bullet["order_index"],
                "original_text": bullet["text"],
                "current_text": bullet["text"],
            }).execute()

    logger.info(
        "Resume uploaded",
        resume_id=resume_id,
        file_type=file_type,
        sections=len(sections_data),
    )

    return {
        "id": resume_id,
        "title": file_title,
        "status": resume_record["status"],
        "file_type": file_type,
        "sections": sections_data,
        "dna_schema": dna_schema,
    }


# ── List ───────────────────────────────────────────────────────────────────────

@router.get("", response_model=list[ResumeListItem])
async def list_resumes(
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
):
    result = (
        supabase.table("resumes")
        .select("id, title, status, original_file_type, created_at, updated_at")
        .eq("user_id", current_user["id"])
        .order("updated_at", desc=True)
        .execute()
    )
    return result.data


# ── Get ────────────────────────────────────────────────────────────────────────

@router.get("/{resume_id}")
async def get_resume(
    resume_id: str,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
):
    result = (
        supabase.table("resumes")
        .select("*")
        .eq("id", resume_id)
        .eq("user_id", current_user["id"])
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Resume not found")

    resume = result.data
    sections_result = (
        supabase.table("resume_sections")
        .select("*")
        .eq("resume_id", resume_id)
        .order("order_index")
        .execute()
    )

    for section in sections_result.data:
        bullets_result = (
            supabase.table("resume_bullets")
            .select("*")
            .eq("section_id", section["id"])
            .order("order_index")
            .execute()
        )
        section["bullets"] = bullets_result.data

    resume["sections"] = sections_result.data
    return resume


# ── Update bullet ──────────────────────────────────────────────────────────────

@router.patch("/{resume_id}/bullets/{bullet_id}")
async def update_bullet(
    resume_id: str,
    bullet_id: str,
    payload: UpdateBulletRequest,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
):
    resume = (
        supabase.table("resumes")
        .select("id")
        .eq("id", resume_id)
        .eq("user_id", current_user["id"])
        .single()
        .execute()
    )
    if not resume.data:
        raise HTTPException(status_code=404, detail="Resume not found")

    result = (
        supabase.table("resume_bullets")
        .update({"current_text": payload.text})
        .eq("id", bullet_id)
        .eq("resume_id", resume_id)
        .execute()
    )
    return result.data[0] if result.data else {}


# ── Lock bullet ────────────────────────────────────────────────────────────────

@router.patch("/{resume_id}/bullets/{bullet_id}/lock")
async def lock_bullet(
    resume_id: str,
    bullet_id: str,
    payload: LockBulletRequest,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
):
    supabase.table("resume_bullets").update(
        {"is_locked": payload.locked}
    ).eq("id", bullet_id).eq("resume_id", resume_id).execute()
    return {"locked": payload.locked}


# ── Delete ─────────────────────────────────────────────────────────────────────

@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resume(
    resume_id: str,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
    settings: Settings = Depends(get_settings),
):
    resume = (
        supabase.table("resumes")
        .select("original_file_path")
        .eq("id", resume_id)
        .eq("user_id", current_user["id"])
        .single()
        .execute()
    )
    if not resume.data:
        raise HTTPException(status_code=404, detail="Resume not found")

    try:
        path = resume.data.get("original_file_path", "")
        if path:
            supabase.storage.from_(settings.supabase_storage_bucket).remove([path])
    except Exception:
        pass

    supabase.table("resumes").delete().eq("id", resume_id).execute()
