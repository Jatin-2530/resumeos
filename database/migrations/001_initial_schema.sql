-- ============================================================================
-- ResumeOS Initial Schema
-- Run in Supabase SQL Editor or via psql
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ── Users ─────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    auth_id     UUID UNIQUE NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    email       TEXT NOT NULL,
    full_name   TEXT,
    avatar_url  TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_users_auth_id ON users(auth_id);
CREATE INDEX idx_users_email ON users(email);

-- Auto-create user record on Supabase auth sign-up
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.users (auth_id, email, full_name, avatar_url)
    VALUES (
        NEW.id,
        NEW.email,
        NEW.raw_user_meta_data->>'full_name',
        NEW.raw_user_meta_data->>'avatar_url'
    )
    ON CONFLICT (auth_id) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- ── Resume Templates ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS resume_templates (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id              UUID REFERENCES users(id) ON DELETE CASCADE,
    name                 TEXT NOT NULL DEFAULT 'Default Template',
    family_type          TEXT DEFAULT 'mba_placement',
    page_width_emu       BIGINT,
    page_height_emu      BIGINT,
    margin_top_emu       BIGINT,
    margin_bottom_emu    BIGINT,
    margin_left_emu      BIGINT,
    margin_right_emu     BIGINT,
    usable_width_emu     BIGINT,
    default_font_family  TEXT DEFAULT 'Calibri',
    default_font_size    NUMERIC(4,1) DEFAULT 10.0,
    created_at           TIMESTAMPTZ DEFAULT NOW()
);

-- ── Layout Constraints ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS layout_constraints (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id           UUID REFERENCES resume_templates(id) ON DELETE CASCADE,
    section_name          TEXT NOT NULL,
    max_lines_per_bullet  INTEGER DEFAULT 2,
    max_chars_per_line    INTEGER,
    font_family           TEXT,
    font_size             NUMERIC(4,1),
    bold                  BOOLEAN DEFAULT FALSE,
    italic                BOOLEAN DEFAULT FALSE,
    indent_level          INTEGER DEFAULT 0,
    space_before_pt       NUMERIC(4,1),
    space_after_pt        NUMERIC(4,1),
    usable_width_pt       NUMERIC(8,2),
    created_at            TIMESTAMPTZ DEFAULT NOW()
);

-- ── Resumes ───────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS resumes (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id              UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    template_id          UUID REFERENCES resume_templates(id),
    title                TEXT NOT NULL DEFAULT 'My Resume',
    original_file_path   TEXT,
    original_file_type   TEXT CHECK (original_file_type IN ('docx', 'pdf')),
    original_file_size   BIGINT,
    status               TEXT DEFAULT 'processing'
                             CHECK (status IN ('processing', 'ready', 'optimizing', 'error')),
    dna_schema           JSONB,
    created_at           TIMESTAMPTZ DEFAULT NOW(),
    updated_at           TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_resumes_user_id ON resumes(user_id);
CREATE INDEX idx_resumes_status  ON resumes(status);
CREATE INDEX idx_resumes_updated ON resumes(updated_at DESC);

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_resumes_updated_at
    BEFORE UPDATE ON resumes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ── Resume Sections ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS resume_sections (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resume_id    UUID NOT NULL REFERENCES resumes(id) ON DELETE CASCADE,
    name         TEXT NOT NULL,
    section_type TEXT,
    order_index  INTEGER NOT NULL,
    style_name   TEXT,
    font_family  TEXT,
    font_size    NUMERIC(4,1),
    bold         BOOLEAN,
    text_color   TEXT,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_sections_resume_id ON resume_sections(resume_id, order_index);

-- ── Resume Bullets ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS resume_bullets (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    section_id       UUID NOT NULL REFERENCES resume_sections(id) ON DELETE CASCADE,
    resume_id        UUID NOT NULL REFERENCES resumes(id) ON DELETE CASCADE,
    order_index      INTEGER NOT NULL,
    original_text    TEXT NOT NULL,
    current_text     TEXT NOT NULL,
    font_family      TEXT,
    font_size        NUMERIC(4,1),
    indent_level     INTEGER DEFAULT 0,
    estimated_lines  INTEGER,
    space_before_pt  NUMERIC(4,1),
    space_after_pt   NUMERIC(4,1),
    is_locked        BOOLEAN DEFAULT FALSE,
    created_at       TIMESTAMPTZ DEFAULT NOW(),
    updated_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_bullets_section_id ON resume_bullets(section_id, order_index);
CREATE INDEX idx_bullets_resume_id  ON resume_bullets(resume_id);

CREATE TRIGGER trg_bullets_updated_at
    BEFORE UPDATE ON resume_bullets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ── Resume Versions ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS resume_versions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resume_id       UUID NOT NULL REFERENCES resumes(id) ON DELETE CASCADE,
    version_number  INTEGER NOT NULL,
    changes         JSONB,
    full_snapshot   JSONB,
    created_by_jd   UUID,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_versions_resume_id ON resume_versions(resume_id, version_number DESC);

-- ── Job Descriptions ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS job_descriptions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title               TEXT,
    company             TEXT,
    raw_text            TEXT NOT NULL,
    extracted_keywords  JSONB DEFAULT '[]',
    skill_clusters      JSONB DEFAULT '{}',
    competencies        JSONB DEFAULT '[]',
    action_verbs        JSONB DEFAULT '[]',
    role_category       TEXT DEFAULT 'other',
    ats_keyword_map     JSONB DEFAULT '{}',
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_jd_user_id ON job_descriptions(user_id);

-- ── AI Generations ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ai_generations (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bullet_id           UUID REFERENCES resume_bullets(id) ON DELETE CASCADE,
    jd_id               UUID REFERENCES job_descriptions(id),
    original_text       TEXT NOT NULL,
    alternatives        JSONB NOT NULL DEFAULT '[]',
    selected_alternative TEXT,
    model_used          TEXT,
    prompt_tokens       INTEGER,
    completion_tokens   INTEGER,
    validation_results  JSONB,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_generations_bullet_id ON ai_generations(bullet_id);

-- ── ATS Reports ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ats_reports (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resume_id             UUID NOT NULL REFERENCES resumes(id) ON DELETE CASCADE,
    jd_id                 UUID REFERENCES job_descriptions(id),
    overall_score         NUMERIC(5,2),
    keyword_coverage      NUMERIC(5,2),
    format_score          NUMERIC(5,2),
    parse_confidence      NUMERIC(5,2),
    missing_keywords      JSONB DEFAULT '[]',
    found_keywords        JSONB DEFAULT '[]',
    section_parse_results JSONB DEFAULT '{}',
    recommendations       JSONB DEFAULT '[]',
    ats_system            TEXT DEFAULT 'internal',
    created_at            TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_ats_reports_resume_id ON ats_reports(resume_id, created_at DESC);

-- ── Recruiter Scores ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS recruiter_scores (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resume_id           UUID NOT NULL REFERENCES resumes(id) ON DELETE CASCADE,
    jd_id               UUID REFERENCES job_descriptions(id),
    persona             TEXT NOT NULL,
    readability_score   NUMERIC(5,2),
    leadership_density  NUMERIC(5,2),
    quantified_impact   NUMERIC(5,2),
    scan_efficiency     NUMERIC(5,2),
    semantic_strength   NUMERIC(5,2),
    clutter_score       NUMERIC(5,2),
    overall_score       NUMERIC(5,2),
    recommendations     JSONB DEFAULT '[]',
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_recruiter_scores_resume_id ON recruiter_scores(resume_id, persona);

-- ── Semantic Metrics ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS semantic_metrics (
    id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resume_id                UUID NOT NULL REFERENCES resumes(id) ON DELETE CASCADE,
    section_id               UUID REFERENCES resume_sections(id) ON DELETE CASCADE,
    avg_info_density         NUMERIC(5,2),
    quantified_impact_count  INTEGER,
    action_verb_strength     NUMERIC(5,2),
    keyword_relevance        NUMERIC(5,2),
    redundancy_score         NUMERIC(5,2),
    created_at               TIMESTAMPTZ DEFAULT NOW()
);
