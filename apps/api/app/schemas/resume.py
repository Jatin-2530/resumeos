from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid


class BulletOut(BaseModel):
    id: str
    section_id: str
    order_index: int
    original_text: str
    current_text: str
    font_family: Optional[str] = None
    font_size: Optional[float] = None
    indent_level: int = 0
    estimated_lines: Optional[int] = None
    is_locked: bool = False


class SectionOut(BaseModel):
    id: str
    resume_id: str
    name: str
    section_type: Optional[str] = None
    order_index: int
    bullets: list[BulletOut] = Field(default_factory=list)


class ResumeOut(BaseModel):
    id: str
    user_id: str
    title: str
    status: str
    original_file_type: Optional[str] = None
    dna_schema: Optional[dict] = None
    sections: list[SectionOut] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ResumeListItem(BaseModel):
    id: str
    title: str
    status: str
    original_file_type: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class UpdateBulletRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=500)


class LockBulletRequest(BaseModel):
    locked: bool
