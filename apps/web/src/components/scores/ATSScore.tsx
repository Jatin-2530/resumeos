"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Shield, CheckCircle, XCircle, TrendingUp } from "lucide-react";
import { cn } from "@/lib/utils";

interface ATSScoreProps {
  resumeId: string;
  jdId: string | null;
  report?: any;
}

function ScoreRing({ score, size = 80 }: { score: number; size?: number }) {
  const radius = (size - 8) / 2;
  const circumference = radius * 2 * Math.PI;
  const strokeDashoffset = circumference - (score / 100) * circumference;
  const color =
    score >= 70 ? "#059669" : score >= 50 ? "#D97706" : "#DC2626";

  return (
    <svg width={size} height={size} className="-rotate-90">
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke="#E5E7EB"
        strokeWidth={6}
      />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke={color}
        strokeWidth={6}
        strokeDasharray={circumference}
        strokeDashoffset={strokeDashoffset}
        strokeLinecap="round"
        style={{ transition: "stroke-dashoffset 0.5s ease" }}
      />
    </svg>
  );
}

export default function ATSScore({ resumeId, jdId, report }: ATSScoreProps) {
  const { data, isLoading } = useQuery({
    queryKey: ["ats-report", resumeId, jdId],
    queryFn: () =>
      api
        .post("/validation/ats", { resume_id: resumeId, jd_id: jdId })
        .then((r) => r.data),
    enabled: !!resumeId,
    initialData: report,
  });

  if (isLoading) {
    return (
      <div className="bg-white rounded-2xl border border-surface-3 p-6">
        <div className="animate-pulse space-y-3">
          <div className="h-4 w-24 bg-surface-2 rounded" />
          <div className="h-20 w-20 bg-surface-2 rounded-full mx-auto" />
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="bg-white rounded-2xl border border-surface-3 p-6 text-center">
        <Shield className="w-8 h-8 text-ink-4 mx-auto mb-2" />
        <p className="text-sm text-ink-3">Run ATS validation to see your score</p>
      </div>
    );
  }

  const scores = [
    { label: "Keywords", value: data.keyword_coverage },
    { label: "Format", value: data.format_score },
    { label: "Parse Confidence", value: data.parse_confidence },
  ];

  return (
    <div className="bg-white rounded-2xl border border-surface-3 p-6">
      <div className="flex items-center gap-2 mb-6">
        <Shield className="w-4 h-4 text-accent" />
        <h3 className="font-semibold text-ink-1 text-sm">ATS Compatibility</h3>
      </div>

      {/* Overall score */}
      <div className="flex items-center gap-6 mb-6">
        <div className="relative">
          <ScoreRing score={data.overall_score} size={88} />
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-xl font-bold text-ink-1">
              {data.overall_score?.toFixed(0)}
            </span>
          </div>
        </div>
        <div className="space-y-2 flex-1">
          {scores.map((s) => (
            <div key={s.label}>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-ink-3">{s.label}</span>
                <span className="font-medium text-ink-1">
                  {s.value?.toFixed(0)}%
                </span>
              </div>
              <div className="h-1.5 bg-surface-2 rounded-full overflow-hidden">
                <div
                  className={cn(
                    "h-full rounded-full transition-all",
                    s.value >= 70
                      ? "bg-success"
                      : s.value >= 50
                      ? "bg-warning"
                      : "bg-danger"
                  )}
                  style={{ width: `${s.value}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Keywords */}
      {data.missing_keywords?.length > 0 && (
        <div className="mb-4">
          <p className="text-xs font-medium text-ink-2 mb-2">
            Missing keywords ({data.missing_keywords.length})
          </p>
          <div className="flex flex-wrap gap-1.5">
            {data.missing_keywords.slice(0, 8).map((kw: string) => (
              <span
                key={kw}
                className="text-xs bg-danger-light text-danger px-2 py-0.5 rounded-full"
              >
                {kw}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Recommendations */}
      {data.recommendations?.length > 0 && (
        <div>
          <p className="text-xs font-medium text-ink-2 mb-2">Recommendations</p>
          <ul className="space-y-1.5">
            {data.recommendations.slice(0, 3).map((rec: string, i: number) => (
              <li key={i} className="flex gap-2 text-xs text-ink-3">
                <TrendingUp className="w-3 h-3 text-accent flex-shrink-0 mt-0.5" />
                {rec}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
