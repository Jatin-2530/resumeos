# ResumeOS

**Constraint-Aware Resume Intelligence Platform**

> AI optimization under strict visual constraints. Every generated bullet preserves your document's exact layout behavior.

---

## What This Is

ResumeOS is not an AI resume builder. It is a structured document intelligence system that:

1. **Extracts your document's DNA** — typography, margins, spacing, section hierarchy
2. **Generates layout-safe alternatives** — Gemini AI constrained to fit within your exact line budget
3. **Validates before you export** — overflow detection without opening Word
4. **Scores against ATS and recruiter personas** — know your weaknesses before applying

The core insight: **character count ≠ visual width**. ResumeOS measures rendered width using font metrics and predicts line wraps — so Gemini never generates bullets that break your layout.

---

## Architecture

```
apps/
  web/          # Next.js 14 + TypeScript + Tailwind (Vercel)
  api/          # FastAPI + Python 3.12 (Railway/Render)

services/       # Python business logic (inside apps/api/)
  docx/         # DOCX parsing (python-docx)
  schema/       # DNA extraction + typography metrics
  layout/       # Constraint engine + overflow detection
  ai/           # Gemini 2.5 provider abstraction + orchestrator
  ats/          # ATS validation (internal heuristic)
  recruiter/    # Recruiter persona simulation
  export/       # DOCX + PDF export (LibreOffice headless)

packages/
  shared-types/ # TypeScript types shared between web and tooling

database/
  migrations/   # Supabase PostgreSQL schema + RLS policies
```

### Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, React, TypeScript, Tailwind CSS |
| State | Zustand + TanStack Query |
| Backend | Python FastAPI |
| Database | Supabase PostgreSQL |
| Auth | Supabase Auth (Google + email) |
| Storage | Supabase Storage |
| AI | Gemini 2.5 Flash + Pro |
| Document | python-docx, LibreOffice headless |
| Typography | fonttools (optional), lookup tables |
| Deployment | Vercel (web) + Railway (api) |

---

## Quick Start

### Prerequisites

- Node.js 20+
- Python 3.12+
- pnpm 9+
- A Supabase project
- A Google Gemini API key

### Setup

```bash
# Clone and setup
git clone <repo>
cd resumeos
./infrastructure/scripts/setup.sh

# Fill in credentials
cp .env.example .env
# Edit .env with your Supabase URL, keys, and Gemini API key
```

### Database

Run in Supabase SQL Editor (in order):

```sql
-- 1. Schema
\i database/migrations/001_initial_schema.sql

-- 2. Row Level Security
\i database/migrations/002_rls_policies.sql
```

Create a storage bucket named `resumes` in Supabase Storage.

### Development

```bash
# Backend (terminal 1)
cd apps/api
source .venv/bin/activate
uvicorn main:app --reload --port 8000

# Frontend (terminal 2)
pnpm dev
```

Or with Docker:

```bash
docker-compose up
```

---

## Core Engineering Concepts

### Document DNA Schema

When you upload a DOCX, ResumeOS extracts a `DocumentDNA` object:

```json
{
  "page": {
    "width_emu": 12192000,
    "usable_width_emu": 9792000,
    "usable_width_pt": 771.0
  },
  "bullet_schema": {
    "typography": {
      "font_family": "Calibri",
      "font_size": 10.0,
      "bold": false
    },
    "constraints": {
      "max_lines_per_bullet": 2,
      "max_chars_per_line": 97,
      "usable_width_pt": 771.0
    }
  }
}
```

All AI generation is constrained against this schema.

### Constraint-Aware Generation Pipeline

```
Bullet text
    ↓
DNA constraints extracted
    ↓
Gemini prompt with line budget injected
    ↓
3 alternatives generated
    ↓
Each alternative: estimate_line_count(text, font, width)
    ↓
Overflow? Re-request with tighter budget
    ↓
Ranked alternatives returned (valid first)
```

### Typography Width Estimation

Character count is a bad proxy for visual width. ResumeOS uses:

```python
# Per-font average character width multipliers
FONT_WIDTH_MULTIPLIERS = {
    "Calibri": 0.480,  # fraction of font size in points
    "Times New Roman": 0.500,
    ...
}

# Word-level greedy wrap simulation
def estimate_line_count(text, font_family, font_size_pt, usable_width_pt) -> int:
    ...
```

---

## API Reference

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/resumes` | Upload DOCX/PDF + extract DNA |
| GET | `/api/v1/resumes` | List user's resumes |
| GET | `/api/v1/resumes/:id` | Get resume with sections/bullets |
| PATCH | `/api/v1/resumes/:id/bullets/:bid` | Update bullet text |
| POST | `/api/v1/jd` | Upload + analyze job description |
| POST | `/api/v1/generation/alternatives` | Generate AI alternatives for a bullet |
| POST | `/api/v1/generation/select` | Apply a selected alternative |
| POST | `/api/v1/generation/batch/:id` | Batch-generate for all bullets |
| POST | `/api/v1/validation/bullet` | Check single bullet layout fit |
| POST | `/api/v1/validation/ats` | Run ATS validation |
| POST | `/api/v1/validation/recruiter` | Run recruiter simulation |
| POST | `/api/v1/preview/:id` | Get full resume layout preview |
| POST | `/api/v1/export/docx` | Export optimized DOCX |
| POST | `/api/v1/export/pdf` | Export optimized PDF (requires LibreOffice) |

---

## Deployment

### Frontend (Vercel)

```bash
vercel --prod
# Set env vars: NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY, NEXT_PUBLIC_API_URL
```

### Backend (Railway)

Connect GitHub repo → set root directory to `apps/api` → Railway detects Dockerfile.

Required env vars:
```
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
SUPABASE_JWT_SECRET
GEMINI_API_KEY
API_SECRET_KEY
ALLOWED_ORIGINS=https://your-vercel-app.vercel.app
```

---

## Engineering Priorities (from PRD)

The system was built in this order — matching the PRD's priority list:

1. ✅ DOCX parser (`services/docx/parser.py`)
2. ✅ Schema extraction (`services/schema/dna_extractor.py`)
3. ✅ Typography engine (`services/schema/typography_analyzer.py`)
4. ✅ Layout validator (`services/layout/constraint_engine.py`)
5. ✅ Gemini rewriting engine (`services/ai/gemini_provider.py` + `orchestrator.py`)
6. ✅ Live preview (`routes/preview.py` + `SideBySidePreview.tsx`)
7. ✅ ATS architecture (`services/ats/validator.py`)
8. ✅ Recruiter simulation (`services/recruiter/simulator.py`)
9. ✅ UI (`apps/web/`)

---

## Future Roadmap

- LibreOffice exact rendering validation before export
- Chrome extension for direct job board integration  
- Persona switching (generate consulting vs PM variant in one click)
- Resume Diff Engine with visual change tracking
- Multi-ATS consensus scoring (Affinda, RChilli, Sovren)
- Academic CV and consulting slide support

---

## Security

- All uploads validated for MIME type (python-magic)
- Files stored in Supabase Storage with signed URLs (1hr expiry)
- Row Level Security on all database tables
- JWT validation on every API request
- Service role key never exposed to client
