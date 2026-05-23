-- ============================================================================
-- ResumeOS Row Level Security Policies
-- Run AFTER 001_initial_schema.sql
-- ============================================================================

-- ── Enable RLS on all tables ──────────────────────────────────────────────────
ALTER TABLE users              ENABLE ROW LEVEL SECURITY;
ALTER TABLE resume_templates   ENABLE ROW LEVEL SECURITY;
ALTER TABLE layout_constraints ENABLE ROW LEVEL SECURITY;
ALTER TABLE resumes            ENABLE ROW LEVEL SECURITY;
ALTER TABLE resume_sections    ENABLE ROW LEVEL SECURITY;
ALTER TABLE resume_bullets     ENABLE ROW LEVEL SECURITY;
ALTER TABLE resume_versions    ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_descriptions   ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_generations     ENABLE ROW LEVEL SECURITY;
ALTER TABLE ats_reports        ENABLE ROW LEVEL SECURITY;
ALTER TABLE recruiter_scores   ENABLE ROW LEVEL SECURITY;
ALTER TABLE semantic_metrics   ENABLE ROW LEVEL SECURITY;

-- ── Helper function: get current user id from auth ────────────────────────────
CREATE OR REPLACE FUNCTION auth_user_id()
RETURNS UUID AS $$
    SELECT id FROM users WHERE auth_id = auth.uid()
$$ LANGUAGE SQL STABLE SECURITY DEFINER;

-- ── users table ───────────────────────────────────────────────────────────────
CREATE POLICY "users_select_own" ON users
    FOR SELECT USING (auth_id = auth.uid());

CREATE POLICY "users_update_own" ON users
    FOR UPDATE USING (auth_id = auth.uid());

-- ── resumes ───────────────────────────────────────────────────────────────────
CREATE POLICY "resumes_all_own" ON resumes
    FOR ALL USING (user_id = auth_user_id());

-- ── resume_sections ───────────────────────────────────────────────────────────
CREATE POLICY "sections_all_own" ON resume_sections
    FOR ALL USING (
        resume_id IN (
            SELECT id FROM resumes WHERE user_id = auth_user_id()
        )
    );

-- ── resume_bullets ────────────────────────────────────────────────────────────
CREATE POLICY "bullets_all_own" ON resume_bullets
    FOR ALL USING (
        resume_id IN (
            SELECT id FROM resumes WHERE user_id = auth_user_id()
        )
    );

-- ── resume_versions ───────────────────────────────────────────────────────────
CREATE POLICY "versions_all_own" ON resume_versions
    FOR ALL USING (
        resume_id IN (
            SELECT id FROM resumes WHERE user_id = auth_user_id()
        )
    );

-- ── job_descriptions ──────────────────────────────────────────────────────────
CREATE POLICY "jd_all_own" ON job_descriptions
    FOR ALL USING (user_id = auth_user_id());

-- ── ai_generations ────────────────────────────────────────────────────────────
CREATE POLICY "generations_all_own" ON ai_generations
    FOR ALL USING (
        bullet_id IN (
            SELECT rb.id FROM resume_bullets rb
            JOIN resumes r ON rb.resume_id = r.id
            WHERE r.user_id = auth_user_id()
        )
    );

-- ── ats_reports ───────────────────────────────────────────────────────────────
CREATE POLICY "ats_reports_all_own" ON ats_reports
    FOR ALL USING (
        resume_id IN (
            SELECT id FROM resumes WHERE user_id = auth_user_id()
        )
    );

-- ── recruiter_scores ──────────────────────────────────────────────────────────
CREATE POLICY "recruiter_scores_all_own" ON recruiter_scores
    FOR ALL USING (
        resume_id IN (
            SELECT id FROM resumes WHERE user_id = auth_user_id()
        )
    );

-- ── semantic_metrics ──────────────────────────────────────────────────────────
CREATE POLICY "semantic_metrics_all_own" ON semantic_metrics
    FOR ALL USING (
        resume_id IN (
            SELECT id FROM resumes WHERE user_id = auth_user_id()
        )
    );

-- ── Service role bypass ───────────────────────────────────────────────────────
-- The FastAPI backend uses service_role key which bypasses RLS.
-- The above policies only apply to anon/authenticated Supabase client calls.

-- ── Storage policies ──────────────────────────────────────────────────────────
-- Run these in Supabase Dashboard > Storage > Policies for the 'resumes' bucket

-- INSERT: users can upload to their own folder
-- (resumes/original/<user_id>/*)
-- SELECT: users can read their own files
-- (resumes/original/<user_id>/*, resumes/generated/<user_id>/*)
-- DELETE: users can delete their own files

-- Example policies (adapt bucket/path as needed):
/*
CREATE POLICY "auth users upload own files"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (bucket_id = 'resumes' AND (storage.foldername(name))[2] = auth.uid()::text);

CREATE POLICY "auth users read own files"
ON storage.objects FOR SELECT
TO authenticated
USING (bucket_id = 'resumes' AND (storage.foldername(name))[2] = auth.uid()::text);

CREATE POLICY "auth users delete own files"
ON storage.objects FOR DELETE
TO authenticated
USING (bucket_id = 'resumes' AND (storage.foldername(name))[2] = auth.uid()::text);
*/
