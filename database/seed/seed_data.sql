-- ============================================================================
-- ResumeOS Seed Data — Development Only
-- Run AFTER migrations. Only for local dev, never run in production.
-- ============================================================================

-- The seed user must match a real auth.users entry.
-- Create the user via Supabase auth first, then get their auth_id.

-- Example: insert a test user (replace UUID with your actual auth user ID)
/*
INSERT INTO users (auth_id, email, full_name)
VALUES (
    '00000000-0000-0000-0000-000000000001'::uuid,
    'test@resumeos.dev',
    'Test User'
)
ON CONFLICT (auth_id) DO NOTHING;
*/

-- ── Sample JD for development ────────────────────────────────────────────────
-- INSERT INTO job_descriptions (user_id, title, company, raw_text, role_category)
-- VALUES (
--     (SELECT id FROM users WHERE email = 'test@resumeos.dev'),
--     'Management Consultant',
--     'McKinsey & Company',
--     'We are seeking a management consultant to join our client service team...',
--     'consulting'
-- );
