#!/usr/bin/env bash
# =============================================================================
# ResumeOS Development Setup Script
# =============================================================================
set -euo pipefail

BLUE='\033[0;34m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
error()   { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

info "Setting up ResumeOS development environment..."

# ── Check prerequisites ───────────────────────────────────────────────────────
command -v node >/dev/null 2>&1 || error "Node.js 20+ is required"
command -v pnpm >/dev/null 2>&1 || error "pnpm is required (npm install -g pnpm)"
command -v python3 >/dev/null 2>&1 || error "Python 3.12+ is required"
command -v docker >/dev/null 2>&1 || warn "Docker not found — backend will need manual setup"

NODE_VERSION=$(node -v | cut -c 2-)
MAJOR=$(echo "$NODE_VERSION" | cut -d. -f1)
if [ "$MAJOR" -lt 20 ]; then
    error "Node.js 20+ required (found $NODE_VERSION)"
fi
success "Node.js $NODE_VERSION"

# ── Environment file ──────────────────────────────────────────────────────────
if [ ! -f ".env" ]; then
    cp .env.example .env
    warn ".env created from .env.example — fill in your Supabase and Gemini credentials"
else
    success ".env already exists"
fi

# ── Install frontend dependencies ─────────────────────────────────────────────
info "Installing frontend dependencies..."
pnpm install
success "Frontend dependencies installed"

# ── Python virtual environment ────────────────────────────────────────────────
info "Setting up Python environment..."
if [ ! -d "apps/api/.venv" ]; then
    python3 -m venv apps/api/.venv
fi
source apps/api/.venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r apps/api/requirements.txt
success "Python dependencies installed"

# ── Check LibreOffice ─────────────────────────────────────────────────────────
if command -v libreoffice >/dev/null 2>&1; then
    success "LibreOffice found at $(which libreoffice)"
else
    warn "LibreOffice not found — PDF export will be disabled"
    warn "Install: brew install libreoffice (macOS) or apt install libreoffice (Ubuntu)"
fi

# ── Temp directories ──────────────────────────────────────────────────────────
mkdir -p /tmp/resumeos
success "Temp directory created"

# ── Print next steps ──────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}Setup complete!${NC}"
echo ""
echo "Next steps:"
echo "  1. Edit .env with your Supabase project URL and keys"
echo "  2. Add your Gemini API key to .env"
echo "  3. Run database migrations in Supabase SQL Editor:"
echo "     database/migrations/001_initial_schema.sql"
echo "     database/migrations/002_rls_policies.sql"
echo "  4. Create a 'resumes' storage bucket in Supabase Storage"
echo "  5. Start the backend: cd apps/api && source .venv/bin/activate && uvicorn main:app --reload"
echo "  6. Start the frontend: pnpm dev (from repo root)"
echo ""
echo "Or use Docker: docker-compose up"
