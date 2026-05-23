"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Plus, FileText, Clock, ArrowUpRight, Upload } from "lucide-react";
import { api } from "@/lib/api";
import { formatDistanceToNow } from "@/lib/utils";
import ResumeUpload from "@/components/upload/ResumeUpload";

export default function DashboardPage() {
  const router = useRouter();
  const [showUpload, setShowUpload] = useState(false);

  const { data: resumes = [], isLoading } = useQuery({
    queryKey: ["resumes"],
    queryFn: () => api.get("/resumes").then((r) => r.data),
  });

  const { data: jds = [] } = useQuery({
    queryKey: ["jds"],
    queryFn: () => api.get("/jd").then((r) => r.data),
  });

  return (
    <div className="max-w-5xl mx-auto px-6 py-10">
      {/* ── Header ──────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-ink-1">Workspace</h1>
          <p className="text-sm text-ink-3 mt-1">
            {resumes.length} resume{resumes.length !== 1 ? "s" : ""} ·{" "}
            {jds.length} job description{jds.length !== 1 ? "s" : ""}
          </p>
        </div>
        <button
          onClick={() => setShowUpload(true)}
          className="inline-flex items-center gap-2 bg-ink-1 text-white px-4 py-2.5 rounded-xl text-sm font-medium hover:bg-ink-2 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Upload resume
        </button>
      </div>

      {/* ── Resumes grid ─────────────────────────────────────────── */}
      <section className="mb-12">
        <h2 className="text-sm font-semibold text-ink-3 uppercase tracking-wider mb-4">
          Resumes
        </h2>

        {isLoading ? (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[...Array(3)].map((_, i) => (
              <div
                key={i}
                className="h-32 bg-surface-2 rounded-2xl animate-pulse"
              />
            ))}
          </div>
        ) : resumes.length === 0 ? (
          <button
            onClick={() => setShowUpload(true)}
            className="w-full border-2 border-dashed border-surface-3 rounded-2xl p-12 text-center hover:border-accent-muted transition-colors group"
          >
            <Upload className="w-8 h-8 text-ink-4 mx-auto mb-3 group-hover:text-accent transition-colors" />
            <p className="text-sm font-medium text-ink-2">
              Upload your first resume
            </p>
            <p className="text-xs text-ink-4 mt-1">
              DOCX supported · up to 10MB
            </p>
          </button>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {resumes.map((resume: any) => (
              <Link
                key={resume.id}
                href={`/resume/${resume.id}`}
                className="group p-5 bg-white rounded-2xl border border-surface-3 hover:border-accent-muted hover:shadow-card-hover transition-all"
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="w-9 h-9 bg-accent-light rounded-xl flex items-center justify-center">
                    <FileText className="w-4 h-4 text-accent" />
                  </div>
                  <ArrowUpRight className="w-4 h-4 text-ink-4 opacity-0 group-hover:opacity-100 transition-opacity" />
                </div>
                <p className="font-medium text-ink-1 text-sm truncate mb-1">
                  {resume.title}
                </p>
                <div className="flex items-center gap-2">
                  <span
                    className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-medium ${
                      resume.status === "ready"
                        ? "bg-success-light text-success"
                        : "bg-warning-light text-warning"
                    }`}
                  >
                    {resume.status}
                  </span>
                  <span className="text-xs text-ink-4 flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {formatDistanceToNow(resume.updated_at)}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </section>

      {/* ── Job descriptions ────────────────────────────────────── */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-ink-3 uppercase tracking-wider">
            Job Descriptions
          </h2>
          <Link
            href="/jd/new"
            className="text-xs text-accent hover:underline font-medium"
          >
            + Add JD
          </Link>
        </div>

        {jds.length === 0 ? (
          <p className="text-sm text-ink-4 py-4">
            No job descriptions yet. Add one to start matching keywords.
          </p>
        ) : (
          <div className="space-y-2">
            {jds.slice(0, 5).map((jd: any) => (
              <div
                key={jd.id}
                className="flex items-center justify-between p-4 bg-white rounded-xl border border-surface-3 text-sm"
              >
                <div>
                  <span className="font-medium text-ink-1">
                    {jd.title || "Untitled role"}
                  </span>
                  {jd.company && (
                    <span className="text-ink-3 ml-2">at {jd.company}</span>
                  )}
                </div>
                <span className="text-xs bg-surface-2 text-ink-3 px-2 py-1 rounded-lg">
                  {jd.role_category}
                </span>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* ── Upload modal ────────────────────────────────────────── */}
      {showUpload && (
        <ResumeUpload
          onClose={() => setShowUpload(false)}
          onSuccess={(id) => router.push(`/resume/${id}`)}
        />
      )}
    </div>
  );
}
