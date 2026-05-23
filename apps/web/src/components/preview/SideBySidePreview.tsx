"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { AlertTriangle, CheckCircle } from "lucide-react";
import { cn } from "@/lib/utils";

interface SideBySidePreviewProps {
  resumeId: string;
  resume: any;
}

function BulletPreviewLine({
  text,
  validation,
}: {
  text: string;
  validation?: { overflow: boolean; estimated_lines: number; max_lines: number };
}) {
  const hasOverflow = validation?.overflow;
  const nearLimit =
    validation && !hasOverflow && validation.estimated_lines >= validation.max_lines;

  return (
    <div
      className={cn(
        "py-0.5 px-2 rounded text-xs font-mono leading-relaxed border-l-2",
        hasOverflow
          ? "border-danger bg-danger/5"
          : nearLimit
          ? "border-warning bg-warning/5"
          : "border-transparent"
      )}
    >
      <span className="text-ink-1">{text}</span>
      {hasOverflow && (
        <span className="ml-2 text-danger text-[10px]">
          ↕ {validation!.estimated_lines} lines (max {validation!.max_lines})
        </span>
      )}
    </div>
  );
}

export default function SideBySidePreview({ resumeId, resume }: SideBySidePreviewProps) {
  const { data: previewData } = useQuery({
    queryKey: ["preview", resumeId],
    queryFn: () =>
      api.post(`/preview/${resumeId}`, {}).then((r) => r.data),
    enabled: !!resumeId,
  });

  const bulletValidations: Record<string, any> = previewData?.bullet_validations || {};

  const overflowCount = Object.values(bulletValidations).filter(
    (v: any) => v.overflow
  ).length;

  return (
    <div className="space-y-4">
      {/* Validation summary */}
      <div
        className={cn(
          "flex items-center gap-3 p-3 rounded-xl border text-sm",
          overflowCount > 0
            ? "bg-danger-light border-danger/20 text-danger"
            : "bg-success-light border-success/20 text-success"
        )}
      >
        {overflowCount > 0 ? (
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
        ) : (
          <CheckCircle className="w-4 h-4 flex-shrink-0" />
        )}
        {overflowCount > 0
          ? `${overflowCount} bullet${overflowCount !== 1 ? "s" : ""} overflow their line limit`
          : "All bullets fit within layout constraints"}
      </div>

      {/* Side-by-side */}
      <div className="grid lg:grid-cols-2 gap-4">
        {/* Original */}
        <div className="bg-white rounded-2xl border border-surface-3 overflow-hidden">
          <div className="bg-surface-1 px-4 py-2.5 border-b border-surface-3">
            <p className="text-xs font-semibold text-ink-3">Original</p>
          </div>
          <div className="p-4 space-y-4">
            {resume.sections?.map((section: any) => (
              <div key={section.id}>
                <p className="text-xs font-bold text-ink-1 uppercase tracking-wider mb-2 border-b border-surface-3 pb-1">
                  {section.name}
                </p>
                <div className="space-y-0.5">
                  {section.bullets?.map((bullet: any) => (
                    <div key={bullet.id} className="text-xs font-mono text-ink-2 leading-relaxed py-0.5">
                      {bullet.original_text}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Optimized */}
        <div className="bg-white rounded-2xl border border-surface-3 overflow-hidden">
          <div className="bg-accent-light px-4 py-2.5 border-b border-accent-muted">
            <p className="text-xs font-semibold text-accent">Optimized</p>
          </div>
          <div className="p-4 space-y-4">
            {resume.sections?.map((section: any) => (
              <div key={section.id}>
                <p className="text-xs font-bold text-ink-1 uppercase tracking-wider mb-2 border-b border-surface-3 pb-1">
                  {section.name}
                </p>
                <div className="space-y-0.5">
                  {section.bullets?.map((bullet: any) => (
                    <BulletPreviewLine
                      key={bullet.id}
                      text={bullet.current_text}
                      validation={bulletValidations[bullet.id]}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
