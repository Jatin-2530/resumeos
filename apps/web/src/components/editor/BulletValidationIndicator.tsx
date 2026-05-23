"use client";

import { useQuery } from "@tanstack/react-query";
import { AlertTriangle } from "lucide-react";
import { api } from "@/lib/api";

interface BulletValidationIndicatorProps {
  text: string;
  resumeId: string;
  sectionName: string;
}

export default function BulletValidationIndicator({
  text,
  resumeId,
  sectionName,
}: BulletValidationIndicatorProps) {
  const { data } = useQuery({
    queryKey: ["bullet-preview", resumeId, sectionName, text],
    queryFn: () =>
      api
        .post("/preview/bullet", {
          text,
          resume_id: resumeId,
          section_name: sectionName,
        })
        .then((r) => r.data),
    staleTime: 30_000,
    enabled: text.length > 10,
  });

  if (!data) return null;

  if (data.overflow) {
    return (
      <div className="flex items-center gap-1.5 mt-1.5">
        <AlertTriangle className="w-3 h-3 text-danger flex-shrink-0" />
        <span className="text-xs text-danger">
          {data.estimated_lines} lines (max {data.max_lines}) — overflow detected
        </span>
      </div>
    );
  }

  if (data.warnings?.length > 0) {
    return (
      <div className="flex items-center gap-1.5 mt-1.5">
        <AlertTriangle className="w-3 h-3 text-warning flex-shrink-0" />
        <span className="text-xs text-warning">Near line limit</span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-1.5 mt-1.5">
      <span className="text-xs text-ink-4">
        {data.estimated_lines} line{data.estimated_lines !== 1 ? "s" : ""} ·{" "}
        {data.char_count} chars
      </span>
    </div>
  );
}
