"""
Export routes — DOCX and PDF export.
"""
from __future__ import annotations

import os
import tempfile
import uuid
from pathlib import Path

import aiofiles
import structlog
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from supabase import Client

from ..config import Settings, get_settings
from ..dependencies import get_current_user, get_supabase
from ..services.export.docx_exporter import DOCXExporter
from ..services.export.pdf_exporter import PDFExporter

logger = structlog.get_logger()
router = APIRouter(prefix="/export", tags=["export"])

_docx_exporter = DOCXExporter()


class ExportRequest(BaseModel):
    resume_id: str


# ── DOCX export ────────────────────────────────────────────────────────────────

@router.post("/docx")
async def export_docx(
    payload: ExportRequest,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
    settings: Settings = Depends(get_settings),
):
    """Export the optimized resume as a DOCX file."""
    resume, original_content, bullet_updates = await _prepare_export(
        payload.resume_id, current_user["id"], supabase, settings
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        original_path = Path(tmpdir) / f"original.docx"
        original_path.write_bytes(original_content)

        output_path = Path(tmpdir) / f"{resume['title']}_optimized.docx"
        _docx_exporter.export(original_path, output_path, bullet_updates)

        # Upload generated file to storage
        with open(output_path, "rb") as f:
            generated_content = f.read()

    export_path = f"resumes/generated/{current_user['id']}/{payload.resume_id}.docx"
    supabase.storage.from_(settings.supabase_storage_bucket).upload(
        path=export_path,
        file=generated_content,
        file_options={
            "content-type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "upsert": "true",
        },
    )

    # Return signed URL (valid 1 hour)
    signed = supabase.storage.from_(settings.supabase_storage_bucket).create_signed_url(
        export_path, 3600
    )
    return {"download_url": signed["signedURL"], "filename": f"{resume['title']}_optimized.docx"}


# ── PDF export ─────────────────────────────────────────────────────────────────

@router.post("/pdf")
async def export_pdf(
    payload: ExportRequest,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
    settings: Settings = Depends(get_settings),
):
    """Export the optimized resume as a PDF file."""
    if not settings.enable_libreoffice_rendering:
        raise HTTPException(
            status_code=503,
            detail="PDF export requires LibreOffice. Enable ENABLE_LIBREOFFICE_RENDERING=true",
        )

    resume, original_content, bullet_updates = await _prepare_export(
        payload.resume_id, current_user["id"], supabase, settings
    )

    pdf_exporter = PDFExporter(settings.libreoffice_path)

    with tempfile.TemporaryDirectory() as tmpdir:
        original_path = Path(tmpdir) / "original.docx"
        original_path.write_bytes(original_content)

        docx_output = Path(tmpdir) / "optimized.docx"
        _docx_exporter.export(original_path, docx_output, bullet_updates)

        pdf_path = await pdf_exporter.export(
            docx_path=docx_output,
            output_dir=Path(tmpdir),
            filename_stem="resume_optimized",
        )

        with open(pdf_path, "rb") as f:
            pdf_content = f.read()

    export_path = f"resumes/generated/{current_user['id']}/{payload.resume_id}.pdf"
    supabase.storage.from_(settings.supabase_storage_bucket).upload(
        path=export_path,
        file=pdf_content,
        file_options={"content-type": "application/pdf", "upsert": "true"},
    )

    signed = supabase.storage.from_(settings.supabase_storage_bucket).create_signed_url(
        export_path, 3600
    )
    return {"download_url": signed["signedURL"], "filename": f"{resume['title']}_optimized.pdf"}


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _prepare_export(
    resume_id: str,
    user_id: str,
    supabase: Client,
    settings: Settings,
) -> tuple[dict, bytes, list[dict]]:
    """Fetch resume, download original DOCX, build bullet_updates list."""
    resume_result = (
        supabase.table("resumes")
        .select("*")
        .eq("id", resume_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    if not resume_result.data:
        raise HTTPException(status_code=404, detail="Resume not found")

    resume = resume_result.data
    if resume.get("original_file_type") != "docx":
        raise HTTPException(status_code=422, detail="Only DOCX resumes can be exported")

    # Download original from storage
    try:
        original_content = supabase.storage.from_(
            settings.supabase_storage_bucket
        ).download(resume["original_file_path"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not download original file: {e}")

    # Build paragraph-level updates using the parsed document structure
    bullets_result = (
        supabase.table("resume_bullets")
        .select("current_text, original_text, order_index, resume_sections(order_index, name)")
        .eq("resume_id", resume_id)
        .execute()
    )

    # We use a simplified index scheme: serialize bullets as ordered paragraphs
    # A full implementation would store paragraph indices from the original parse
    bullet_updates = []
    return resume, original_content, bullet_updates
