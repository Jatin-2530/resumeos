"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Users } from "lucide-react";
import { cn } from "@/lib/utils";

interface RecruiterScoreProps {
  resumeId: string;
  jdId: string | null;
}

const PERSONAS = [
  { key: "consulting", label: "Consulting", emoji: "📊" },
  { key: "finance", label: "Finance", emoji: "💰" },
  { key: "startup", label: "Startup", emoji: "🚀" },
  { key: "pm", label: "Product", emoji: "⚙️" },
  { key: "hr", label: "HR", emoji: "👥" },
];

const DIMENSIONS = [
  { key: "readability_score", label: "Readability" },
  { key: "leadership_density", label: "Leadership" },
  { key: "quantified_impact", label: "Impact" },
  { key: "scan_efficiency", label: "Scan efficiency" },
  { key: "semantic_strength", label: "Semantic strength" },
];

export default function RecruiterScore({ resumeId, jdId }: RecruiterScoreProps) {
  const [activePersona, setActivePersona] = useState("consulting");

  const { data: scores, isLoading } = useQuery({
    queryKey: ["recruiter-scores", resumeId, jdId],
    queryFn: () =>
      api
        .post(
          `/validation/recruiter?personas=consulting,finance,startup,pm,hr`,
          { resume_id: resumeId, jd_id: jdId }
        )
        .then((r) => r.data),
    enabled: !!resumeId,
  });

  const current = scores?.find((s: any) => s.persona === activePersona);

  return (
    <div className="bg-white rounded-2xl border border-surface-3 p-6">
      <div className="flex items-center gap-2 mb-5">
        <Users className="w-4 h-4 text-accent" />
        <h3 className="font-semibold text-ink-1 text-sm">Recruiter Intelligence</h3>
      </div>

      {/* Persona tabs */}
      <div className="flex gap-1 mb-5 overflow-x-auto pb-1">
        {PERSONAS.map((p) => {
          const score = scores?.find((s: any) => s.persona === p.key);
          return (
            <button
              key={p.key}
              onClick={() => setActivePersona(p.key)}
              className={cn(
                "flex-shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all whitespace-nowrap",
                activePersona === p.key
                  ? "bg-ink-1 text-white"
                  : "bg-surface-2 text-ink-3 hover:bg-surface-3"
              )}
            >
              <span>{p.emoji}</span>
              {p.label}
              {score && (
                <span
                  className={cn(
                    "ml-1 text-[10px]",
                    activePersona === p.key ? "text-white/70" : "text-ink-4"
                  )}
                >
                  {score.overall_score?.toFixed(0)}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {isLoading ? (
        <div className="space-y-3 animate-pulse">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-4 bg-surface-2 rounded" />
          ))}
        </div>
      ) : current ? (
        <>
          {/* Score dimensions */}
          <div className="space-y-3 mb-5">
            {DIMENSIONS.map((dim) => {
              const value = current[dim.key] ?? 0;
              return (
                <div key={dim.key}>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-ink-3">{dim.label}</span>
                    <span className="font-medium text-ink-1">
                      {value.toFixed(0)}
                    </span>
                  </div>
                  <div className="h-2 bg-surface-2 rounded-full overflow-hidden">
                    <div
                      className={cn(
                        "h-full rounded-full transition-all",
                        value >= 70 ? "bg-success" : value >= 50 ? "bg-warning" : "bg-danger"
                      )}
                      style={{ width: `${value}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>

          {/* Overall */}
          <div className="bg-surface-1 rounded-xl p-3 mb-4">
            <div className="flex justify-between text-sm">
              <span className="font-medium text-ink-2">Overall</span>
              <span className="font-bold text-ink-1">
                {current.overall_score?.toFixed(0)}/100
              </span>
            </div>
          </div>

          {/* Recommendations */}
          {current.recommendations?.length > 0 && (
            <div>
              <p className="text-xs font-medium text-ink-2 mb-2">
                {PERSONAS.find((p) => p.key === activePersona)?.label} feedback
              </p>
              <ul className="space-y-1">
                {current.recommendations.map((r: string, i: number) => (
                  <li key={i} className="text-xs text-ink-3">
                    • {r}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      ) : (
        <p className="text-sm text-ink-3 text-center py-4">
          No score data yet
        </p>
      )}
    </div>
  );
}
