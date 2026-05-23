import Link from "next/link";
import {
  ArrowRight,
  Shield,
  Zap,
  BarChart3,
  FileText,
  CheckCircle,
  Lock,
} from "lucide-react";

const FEATURES = [
  {
    icon: Lock,
    title: "Resume DNA Lock",
    description:
      "Extracts your document's formatting blueprint. Every AI modification is constrained to preserve identical layout behavior.",
  },
  {
    icon: Zap,
    title: "Constraint-Aware Generation",
    description:
      "Gemini generates alternatives that fit within your exact typography constraints — never breaking line count or section height.",
  },
  {
    icon: Shield,
    title: "ATS Validation",
    description:
      "Internal ATS scoring with keyword coverage analysis. Know exactly which keywords are missing before you apply.",
  },
  {
    icon: BarChart3,
    title: "Recruiter Intelligence",
    description:
      "Simulate how a consulting, finance, or startup recruiter reads your resume. Get persona-specific optimization signals.",
  },
  {
    icon: FileText,
    title: "DOCX + PDF Export",
    description:
      "Export perfectly formatted files. LibreOffice headless ensures pixel-perfect rendering fidelity.",
  },
  {
    icon: CheckCircle,
    title: "Semantic Density",
    description:
      "Measures informational value per line. Compress verbose content while preserving every signal recruiters care about.",
  },
];

const METRICS = [
  { value: "100%", label: "Layout Preserved" },
  { value: "3x", label: "Faster Optimization" },
  { value: "40+", label: "ATS Signals Checked" },
  { value: "6", label: "Recruiter Personas" },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-white">
      {/* ── Nav ─────────────────────────────────────────────────────────── */}
      <nav className="border-b border-surface-3 bg-white/80 backdrop-blur sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
          <span className="font-semibold text-ink-1 tracking-tight">
            Resume<span className="text-accent">OS</span>
          </span>
          <div className="flex items-center gap-3">
            <Link
              href="/login"
              className="text-sm text-ink-2 hover:text-ink-1 transition-colors"
            >
              Sign in
            </Link>
            <Link
              href="/login"
              className="text-sm bg-ink-1 text-white px-4 py-2 rounded-lg hover:bg-ink-2 transition-colors"
            >
              Get started
            </Link>
          </div>
        </div>
      </nav>

      {/* ── Hero ────────────────────────────────────────────────────────── */}
      <section className="max-w-4xl mx-auto px-6 pt-24 pb-20 text-center">
        <div className="inline-flex items-center gap-2 bg-accent-light text-accent text-xs font-medium px-3 py-1.5 rounded-full mb-8">
          <span className="w-1.5 h-1.5 bg-accent rounded-full animate-pulse" />
          AI optimization under strict visual constraints
        </div>

        <h1 className="text-5xl font-bold text-ink-1 leading-tight tracking-tight mb-6">
          Resume intelligence that{" "}
          <span className="text-accent">preserves your format</span>
        </h1>

        <p className="text-xl text-ink-3 leading-relaxed max-w-2xl mx-auto mb-10">
          ResumeOS extracts your document's formatting DNA, then optimizes
          every bullet with Gemini AI — without ever breaking your layout.
          Built for MBA placement and management consulting standards.
        </p>

        <div className="flex items-center justify-center gap-4">
          <Link
            href="/login"
            className="inline-flex items-center gap-2 bg-ink-1 text-white px-6 py-3 rounded-xl font-medium hover:bg-ink-2 transition-colors"
          >
            Start optimizing <ArrowRight className="w-4 h-4" />
          </Link>
          <a
            href="#features"
            className="text-sm text-ink-3 hover:text-ink-1 transition-colors"
          >
            See how it works
          </a>
        </div>
      </section>

      {/* ── Metrics ─────────────────────────────────────────────────────── */}
      <section className="border-y border-surface-3 bg-surface-1">
        <div className="max-w-4xl mx-auto px-6 py-12 grid grid-cols-2 md:grid-cols-4 gap-8">
          {METRICS.map((m) => (
            <div key={m.label} className="text-center">
              <div className="text-3xl font-bold text-ink-1 mb-1">{m.value}</div>
              <div className="text-sm text-ink-3">{m.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Features ────────────────────────────────────────────────────── */}
      <section id="features" className="max-w-6xl mx-auto px-6 py-24">
        <div className="text-center mb-16">
          <h2 className="text-3xl font-bold text-ink-1 mb-4">
            Not an AI resume builder
          </h2>
          <p className="text-lg text-ink-3 max-w-xl mx-auto">
            A structured document intelligence system. Every component is
            designed around layout preservation first.
          </p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {FEATURES.map((f) => (
            <div
              key={f.title}
              className="p-6 rounded-2xl border border-surface-3 hover:border-accent-muted hover:shadow-card-hover transition-all"
            >
              <div className="w-10 h-10 bg-accent-light rounded-xl flex items-center justify-center mb-4">
                <f.icon className="w-5 h-5 text-accent" />
              </div>
              <h3 className="font-semibold text-ink-1 mb-2">{f.title}</h3>
              <p className="text-sm text-ink-3 leading-relaxed">{f.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── CTA ─────────────────────────────────────────────────────────── */}
      <section className="bg-ink-1 text-white">
        <div className="max-w-2xl mx-auto px-6 py-20 text-center">
          <h2 className="text-3xl font-bold mb-4">
            Upload your resume. Get your DNA.
          </h2>
          <p className="text-ink-4 mb-8 leading-relaxed">
            ResumeOS works with any .docx resume. Upload once, optimize
            endlessly — every change respects your original formatting constraints.
          </p>
          <Link
            href="/login"
            className="inline-flex items-center gap-2 bg-white text-ink-1 px-6 py-3 rounded-xl font-medium hover:bg-surface-2 transition-colors"
          >
            Upload your resume <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      {/* ── Footer ──────────────────────────────────────────────────────── */}
      <footer className="border-t border-surface-3">
        <div className="max-w-6xl mx-auto px-6 py-8 flex items-center justify-between text-sm text-ink-4">
          <span>
            Resume<span className="text-ink-3">OS</span>
          </span>
          <span>Constraint-Aware Resume Intelligence Platform</span>
        </div>
      </footer>
    </div>
  );
}
