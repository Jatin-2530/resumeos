"use client";

import { useState } from "react";
import { X, AlertTriangle, CheckCircle } from "lucide-react";
import { cn } from "@/lib/utils";

interface Alternative {
  text: string;
  estimated_lines: number;
  ats_score: number;
  overflow_warning: boolean;
}

interface GenerationData {
  generation_id: string;
  original_text: string;
  alternatives: Alternative[];
  constraints: {
    max_lines: number;
    max_chars_per_line: number;
    font_family: string;
    font_size: number;
  };
}

interface AlternativeSelectorProps {
  data: GenerationData;
  onSelect: (text: string) => void;
  onClose: () => void;
}

export default function AlternativeSelector({
  data,
  onSelect,
  onClose,
}: AlternativeSelectorProps) {
  const [selected, setSelected] = useState<string | null>(null);

  return (
    <div className="mt-3 p-4 bg-surface-1 rounded-xl border border-surface-3 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div>
          <p className="text-xs font-semibold text-ink-1">AI Alternatives</p>
          <p className="text-xs text-ink-4 mt-0.5">
            {data.constraints.font_family} {data.constraints.font_size}pt ·
            max {data.constraints.max_lines} lines ·
            ~{data.constraints.max_chars_per_line} chars/line
          </p>
        </div>
        <button
          onClick={onClose}
          className="w-6 h-6 flex items-center justify-center rounded-lg hover:bg-surface-2 transition-colors"
        >
          <X className="w-3.5 h-3.5 text-ink-3" />
        </button>
      </div>

      {/* Original */}
      <div className="mb-3 p-3 bg-white rounded-lg border border-surface-3">
        <p className="text-xs font-medium text-ink-3 mb-1">Original</p>
        <p className="text-xs text-ink-2 font-mono leading-relaxed">
          {data.original_text}
        </p>
      </div>

      {/* Alternatives */}
      <div className="space-y-2">
        {data.alternatives.map((alt, idx) => (
          <button
            key={idx}
            onClick={() => setSelected(alt.text)}
            className={cn(
              "w-full text-left p-3 rounded-lg border transition-all",
              selected === alt.text
                ? "border-accent bg-accent-light"
                : "border-surface-3 bg-white hover:border-accent-muted"
            )}
          >
            <div className="flex items-start justify-between gap-2 mb-2">
              <div className="flex items-center gap-1.5">
                {alt.overflow_warning ? (
                  <AlertTriangle className="w-3 h-3 text-warning flex-shrink-0" />
                ) : (
                  <CheckCircle className="w-3 h-3 text-success flex-shrink-0" />
                )}
                <span className="text-xs text-ink-3">
                  {alt.estimated_lines} line{alt.estimated_lines !== 1 ? "s" : ""}
                </span>
              </div>
              <div className="flex items-center gap-1">
                <span className="text-xs text-ink-4">ATS</span>
                <span
                  className={cn(
                    "text-xs font-semibold",
                    alt.ats_score >= 70
                      ? "text-success"
                      : alt.ats_score >= 50
                      ? "text-warning"
                      : "text-danger"
                  )}
                >
                  {alt.ats_score.toFixed(0)}
                </span>
              </div>
            </div>
            <p className="text-xs text-ink-1 font-mono leading-relaxed">
              {alt.text}
            </p>
          </button>
        ))}
      </div>

      {/* Apply */}
      <div className="mt-3 flex gap-2">
        <button
          onClick={onClose}
          className="flex-1 border border-surface-3 text-xs text-ink-2 py-2 rounded-lg hover:bg-surface-2 transition-colors"
        >
          Keep original
        </button>
        <button
          onClick={() => selected && onSelect(selected)}
          disabled={!selected}
          className="flex-1 bg-ink-1 text-white text-xs py-2 rounded-lg hover:bg-ink-2 disabled:opacity-40 transition-colors"
        >
          Apply selected
        </button>
      </div>
    </div>
  );
}
