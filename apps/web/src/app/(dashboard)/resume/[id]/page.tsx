"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import BulletEditor from "@/components/editor/BulletEditor";
import ATSScore from "@/components/scores/ATSScore";
import RecruiterScore from "@/components/scores/RecruiterScore";
import SideBySidePreview from "@/components/preview/SideBySidePreview";
import JDSelector from "@/components/jd/JDSelector";
import { Download, BarChart3, Eye, Wand2 } from "lucide-react";

type Tab = "editor" | "preview" | "scores";

export default function ResumePage() {
  const { id } = useParams<{ id: string }>();
  const [activeTab, setActiveTab] = useState<Tab>("editor");
  const [selectedJDId, setSelectedJDId] = useState<string | null>(null);

  const { data: resume, isLoading } = useQuery({
    queryKey: ["resume", id],
    queryFn: () => api.get(`/resumes/${id}`).then((r) => r.data),
    enabled: !!id,
  });

  const { data: atsReport } = useQuery({
    queryKey: ["ats-report", id, selectedJDId],
    queryFn: () =>
      api
        .post("/validation/ats", { resume_id: id, jd_id: selectedJDId })
        .then((r) => r.data),
    enabled: !!id,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-6 h-6 border-2 border-accent/30 border-t-accent rounded-full animate-spin" />
      </div>
    );
  }

  if (!resume) {
    return (
      <div className="text-center py-20 text-ink-3">Resume not found.</div>
    );
  }

  const tabs: { key: Tab; label: string; icon: React.ElementType }[] = [
    { key: "editor", label: "Editor", icon: Wand2 },
    { key: "preview", label: "Preview", icon: Eye },
    { key: "scores", label: "Scores", icon: BarChart3 },
  ];

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      {/* ── Header ──────────────────────────────────────────────── */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-ink-1">{resume.title}</h1>
          <p className="text-sm text-ink-3 mt-0.5">
            {resume.sections?.length || 0} sections ·{" "}
            {resume.sections?.reduce(
              (acc: number, s: any) => acc + (s.bullets?.length || 0),
              0
            )}{" "}
            bullets
          </p>
        </div>

        <div className="flex items-center gap-3">
          <JDSelector
            selectedId={selectedJDId}
            onSelect={setSelectedJDId}
          />
          <button className="inline-flex items-center gap-2 border border-surface-3 bg-white text-sm text-ink-2 px-3 py-2 rounded-xl hover:bg-surface-1 transition-colors">
            <Download className="w-4 h-4" />
            Export
          </button>
        </div>
      </div>

      {/* ── Tabs ─────────────────────────────────────────────────── */}
      <div className="flex gap-1 bg-surface-2 rounded-xl p-1 w-fit mb-6">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              activeTab === tab.key
                ? "bg-white text-ink-1 shadow-card"
                : "text-ink-3 hover:text-ink-2"
            }`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* ── Tab content ──────────────────────────────────────────── */}
      {activeTab === "editor" && (
        <BulletEditor
          resume={resume}
          jdId={selectedJDId}
        />
      )}

      {activeTab === "preview" && (
        <SideBySidePreview resumeId={id} resume={resume} />
      )}

      {activeTab === "scores" && (
        <div className="grid lg:grid-cols-2 gap-6">
          <ATSScore resumeId={id} jdId={selectedJDId} report={atsReport} />
          <RecruiterScore resumeId={id} jdId={selectedJDId} />
        </div>
      )}
    </div>
  );
}
