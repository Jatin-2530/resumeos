from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ATSReportOut(BaseModel):
    id: str
    resume_id: str
    jd_id: Optional[str] = None
    overall_score: float
    keyword_coverage: float
    format_score: float
    parse_confidence: float
    missing_keywords: list[str]
    found_keywords: list[str]
    section_parse_results: dict
    recommendations: list[str]
    ats_system: str = "internal"
    created_at: datetime


class RecruiterScoreOut(BaseModel):
    id: str
    resume_id: str
    persona: str
    readability_score: float
    leadership_density: float
    quantified_impact: float
    scan_efficiency: float
    semantic_strength: float
    clutter_score: float
    overall_score: float
    recommendations: list[str]
    created_at: datetime


class JDAnalysisOut(BaseModel):
    id: str
    title: Optional[str] = None
    company: Optional[str] = None
    extracted_keywords: list[str]
    skill_clusters: dict[str, list[str]]
    competencies: list[str]
    action_verbs: list[str]
    role_category: Optional[str] = None
    ats_keyword_map: dict[str, float]


class GenerationAlternative(BaseModel):
    text: str
    estimated_lines: int
    ats_score: float
    overflow_warning: bool = False


class GenerateAlternativesRequest(BaseModel):
    bullet_id: str
    jd_id: str
    num_alternatives: int = Field(default=3, ge=1, le=5)
    use_pro_model: bool = False


class GenerateAlternativesOut(BaseModel):
    generation_id: str
    bullet_id: str
    original_text: str
    alternatives: list[GenerationAlternative]
    constraints: dict


class SelectAlternativeRequest(BaseModel):
    generation_id: str
    selected_text: str


class ValidationResult(BaseModel):
    is_valid: bool
    estimated_lines: int
    max_lines: int
    overflow: bool
    overflow_pixels: float = 0.0
    warnings: list[str] = Field(default_factory=list)
