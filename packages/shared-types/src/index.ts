// ── Document DNA ──────────────────────────────────────────────────────────────
export interface PageMetadata {
  width_emu: number;
  height_emu: number;
  margin_top_emu: number;
  margin_bottom_emu: number;
  margin_left_emu: number;
  margin_right_emu: number;
  usable_width_emu: number;
}

export interface TypographyMetadata {
  font_family: string;
  font_size: number;
  bold: boolean;
  italic: boolean;
  color?: string;
  all_caps: boolean;
  alignment: string;
}

export interface SpacingMetadata {
  space_before_pt: number;
  space_after_pt: number;
  line_spacing?: number;
  line_spacing_rule?: string;
}

export interface ConstraintMetadata {
  max_lines_per_bullet: number;
  max_chars_per_line: number;
  usable_width_pt: number;
  indent_left_pt: number;
  estimated_chars_per_line: number;
}

export interface BulletSchema {
  style_name: string;
  typography: TypographyMetadata;
  spacing: SpacingMetadata;
  indent_left_emu: number;
  constraints: ConstraintMetadata;
}

export interface SectionSchema {
  name: string;
  section_type: string;
  order_index: number;
  style_name: string;
  typography: TypographyMetadata;
  spacing: SpacingMetadata;
  bullet_schema?: BulletSchema;
}

export interface DocumentDNA {
  page: PageMetadata;
  default_font_family: string;
  default_font_size: number;
  sections: SectionSchema[];
  bullet_schema: BulletSchema;
  template_family: string;
  raw_section_names: string[];
}

// ── Resume ────────────────────────────────────────────────────────────────────
export interface Bullet {
  id: string;
  section_id: string;
  resume_id: string;
  order_index: number;
  original_text: string;
  current_text: string;
  font_family?: string;
  font_size?: number;
  indent_level: number;
  estimated_lines?: number;
  is_locked: boolean;
  created_at: string;
  updated_at: string;
}

export interface Section {
  id: string;
  resume_id: string;
  name: string;
  section_type?: string;
  order_index: number;
  bullets: Bullet[];
}

export interface Resume {
  id: string;
  user_id: string;
  title: string;
  status: "processing" | "ready" | "optimizing" | "error";
  original_file_type?: "docx" | "pdf";
  dna_schema?: DocumentDNA;
  sections: Section[];
  created_at: string;
  updated_at: string;
}

// ── Job Description ───────────────────────────────────────────────────────────
export interface JobDescription {
  id: string;
  user_id: string;
  title?: string;
  company?: string;
  raw_text: string;
  extracted_keywords: string[];
  skill_clusters: Record<string, string[]>;
  competencies: string[];
  action_verbs: string[];
  role_category: string;
  ats_keyword_map: Record<string, number>;
  created_at: string;
}

// ── ATS ───────────────────────────────────────────────────────────────────────
export interface ATSReport {
  id: string;
  resume_id: string;
  jd_id?: string;
  overall_score: number;
  keyword_coverage: number;
  format_score: number;
  parse_confidence: number;
  missing_keywords: string[];
  found_keywords: string[];
  section_parse_results: Record<string, any>;
  recommendations: string[];
  ats_system: string;
  created_at: string;
}

// ── Recruiter ─────────────────────────────────────────────────────────────────
export interface RecruiterScore {
  id: string;
  resume_id: string;
  persona: string;
  readability_score: number;
  leadership_density: number;
  quantified_impact: number;
  scan_efficiency: number;
  semantic_strength: number;
  clutter_score: number;
  overall_score: number;
  recommendations: string[];
  created_at: string;
}

// ── Generation ────────────────────────────────────────────────────────────────
export interface GenerationAlternative {
  text: string;
  estimated_lines: number;
  ats_score: number;
  overflow_warning: boolean;
}

export interface GenerationResult {
  generation_id: string;
  bullet_id: string;
  original_text: string;
  alternatives: GenerationAlternative[];
  constraints: ConstraintMetadata;
}

// ── Validation ────────────────────────────────────────────────────────────────
export interface BulletValidation {
  is_valid: boolean;
  estimated_lines: number;
  max_lines: number;
  overflow: boolean;
  overflow_lines: number;
  warnings: string[];
  metrics: Record<string, any>;
}
