"use client";

import { useState, useCallback } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { Wand2, Lock, Unlock, ChevronDown, ChevronUp, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import AlternativeSelector from "./AlternativeSelector";
import BulletValidationIndicator from "./BulletValidationIndicator";

interface Bullet {
  id: string;
  current_text: string;
  original_text: string;
  is_locked: boolean;
  order_index: number;
  estimated_lines?: number;
}

interface Section {
  id: string;
  name: string;
  section_type: string;
  order_index: number;
  bullets: Bullet[];
}

interface BulletEditorProps {
  resume: {
    id: string;
    title: string;
    sections: Section[];
    dna_schema?: any;
  };
  jdId: string | null;
}

export default function BulletEditor({ resume, jdId }: BulletEditorProps) {
  const [collapsedSections, setCollapsedSections] = useState<Set<string>>(
    new Set()
  );
  const [activeGeneration, setActiveGeneration] = useState<string | null>(null);
  const [generationData, setGenerationData] = useState<Record<string, any>>({});
  const queryClient = useQueryClient();

  const toggleSection = (sectionId: string) => {
    setCollapsedSections((prev) => {
      const next = new Set(prev);
      if (next.has(sectionId)) next.delete(sectionId);
      else next.add(sectionId);
      return next;
    });
  };

  const lockMutation = useMutation({
    mutationFn: ({ bulletId, locked }: { bulletId: string; locked: boolean }) =>
      api.patch(`/resumes/${resume.id}/bullets/${bulletId}/lock`, { locked }),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["resume", resume.id] }),
  });

  const generateMutation = useMutation({
    mutationFn: (bulletId: string) =>
      api
        .post("/generation/alternatives", {
          bullet_id: bulletId,
          jd_id: jdId || "",
          num_alternatives: 3,
        })
        .then((r) => r.data),
    onSuccess: (data, bulletId) => {
      setGenerationData((prev) => ({ ...prev, [bulletId]: data }));
      setActiveGeneration(bulletId);
    },
    onError: () => toast.error("Generation failed. Check your JD is selected."),
  });

  const selectMutation = useMutation({
    mutationFn: ({
      generationId,
      selectedText,
    }: {
      generationId: string;
      selectedText: string;
    }) =>
      api.post("/generation/select", {
        generation_id: generationId,
        selected_text: selectedText,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["resume", resume.id] });
      setActiveGeneration(null);
      toast.success("Bullet updated");
    },
  });

  return (
    <div className="space-y-4">
      {!jdId && (
        <div className="bg-warning-light border border-warning/20 rounded-xl p-4 text-sm text-warning">
          Select a job description above to enable AI optimization
        </div>
      )}

      {resume.sections.map((section) => {
        const isCollapsed = collapsedSections.has(section.id);
        const sectionBullets = section.bullets || [];

        return (
          <div
            key={section.id}
            className="bg-white rounded-2xl border border-surface-3 overflow-hidden"
          >
            {/* Section header */}
            <button
              onClick={() => toggleSection(section.id)}
              className="w-full flex items-center justify-between p-4 hover:bg-surface-1 transition-colors"
            >
              <div className="flex items-center gap-3">
                <span className="font-semibold text-ink-1 text-sm">
                  {section.name}
                </span>
                <span className="text-xs bg-surface-2 text-ink-3 px-2 py-0.5 rounded-full">
                  {sectionBullets.length} bullet{sectionBullets.length !== 1 ? "s" : ""}
                </span>
              </div>
              {isCollapsed ? (
                <ChevronDown className="w-4 h-4 text-ink-4" />
              ) : (
                <ChevronUp className="w-4 h-4 text-ink-4" />
              )}
            </button>

            {/* Bullets */}
            {!isCollapsed && (
              <div className="divide-y divide-surface-3 border-t border-surface-3">
                {sectionBullets.map((bullet) => (
                  <div
                    key={bullet.id}
                    className={cn(
                      "p-4 transition-colors",
                      bullet.is_locked ? "bg-surface-1 opacity-70" : ""
                    )}
                  >
                    <div className="flex items-start gap-3">
                      {/* Lock toggle */}
                      <button
                        onClick={() =>
                          lockMutation.mutate({
                            bulletId: bullet.id,
                            locked: !bullet.is_locked,
                          })
                        }
                        className="mt-0.5 text-ink-4 hover:text-ink-2 transition-colors flex-shrink-0"
                        title={bullet.is_locked ? "Unlock bullet" : "Lock bullet"}
                      >
                        {bullet.is_locked ? (
                          <Lock className="w-3.5 h-3.5 text-warning" />
                        ) : (
                          <Unlock className="w-3.5 h-3.5" />
                        )}
                      </button>

                      {/* Bullet text */}
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-ink-1 leading-relaxed font-mono">
                          {bullet.current_text}
                        </p>
                        <BulletValidationIndicator
                          text={bullet.current_text}
                          resumeId={resume.id}
                          sectionName={section.name}
                        />
                      </div>

                      {/* Optimize button */}
                      {!bullet.is_locked && (
                        <button
                          onClick={() => generateMutation.mutate(bullet.id)}
                          disabled={
                            generateMutation.isPending ||
                            !jdId
                          }
                          className="flex-shrink-0 inline-flex items-center gap-1.5 text-xs bg-accent-light text-accent px-3 py-1.5 rounded-lg hover:bg-accent-muted disabled:opacity-40 transition-colors"
                        >
                          {generateMutation.isPending &&
                          generateMutation.variables === bullet.id ? (
                            <Loader2 className="w-3 h-3 animate-spin" />
                          ) : (
                            <Wand2 className="w-3 h-3" />
                          )}
                          Optimize
                        </button>
                      )}
                    </div>

                    {/* Alternative selector */}
                    {activeGeneration === bullet.id &&
                      generationData[bullet.id] && (
                        <AlternativeSelector
                          data={generationData[bullet.id]}
                          onSelect={(text) =>
                            selectMutation.mutate({
                              generationId: generationData[bullet.id].generation_id,
                              selectedText: text,
                            })
                          }
                          onClose={() => setActiveGeneration(null)}
                        />
                      )}
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
