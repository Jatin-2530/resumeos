"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { ChevronDown, Plus, FileSearch } from "lucide-react";
import { cn } from "@/lib/utils";

interface JDSelectorProps {
  selectedId: string | null;
  onSelect: (id: string | null) => void;
}

export default function JDSelector({ selectedId, onSelect }: JDSelectorProps) {
  const [open, setOpen] = useState(false);

  const { data: jds = [] } = useQuery({
    queryKey: ["jds"],
    queryFn: () => api.get("/jd").then((r) => r.data),
  });

  const selected = jds.find((j: any) => j.id === selectedId);

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className={cn(
          "inline-flex items-center gap-2 border rounded-xl px-3 py-2 text-sm transition-colors",
          selectedId
            ? "border-accent bg-accent-light text-accent"
            : "border-surface-3 bg-white text-ink-3 hover:bg-surface-1"
        )}
      >
        <FileSearch className="w-4 h-4" />
        <span className="max-w-32 truncate">
          {selected ? (selected.title || selected.company || "Selected JD") : "Select JD"}
        </span>
        <ChevronDown className="w-3.5 h-3.5 flex-shrink-0" />
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-1 w-64 bg-white rounded-xl border border-surface-3 shadow-modal z-30 animate-fade-in">
          <div className="p-2 max-h-56 overflow-y-auto custom-scroll">
            {jds.length === 0 ? (
              <p className="text-xs text-ink-4 text-center py-3">
                No job descriptions yet
              </p>
            ) : (
              <>
                {selectedId && (
                  <button
                    onClick={() => { onSelect(null); setOpen(false); }}
                    className="w-full text-left px-3 py-2 text-xs text-ink-3 hover:bg-surface-1 rounded-lg transition-colors mb-1"
                  >
                    Clear selection
                  </button>
                )}
                {jds.map((jd: any) => (
                  <button
                    key={jd.id}
                    onClick={() => { onSelect(jd.id); setOpen(false); }}
                    className={cn(
                      "w-full text-left px-3 py-2 rounded-lg text-xs transition-colors",
                      selectedId === jd.id
                        ? "bg-accent-light text-accent"
                        : "hover:bg-surface-1 text-ink-2"
                    )}
                  >
                    <p className="font-medium truncate">
                      {jd.title || "Untitled role"}
                    </p>
                    {jd.company && (
                      <p className="text-ink-4 text-[10px]">{jd.company}</p>
                    )}
                  </button>
                ))}
              </>
            )}
          </div>
          <div className="border-t border-surface-3 p-2">
            <a
              href="/jd/new"
              className="flex items-center gap-2 px-3 py-2 text-xs text-accent hover:bg-accent-light rounded-lg transition-colors"
            >
              <Plus className="w-3 h-3" />
              Add new JD
            </a>
          </div>
        </div>
      )}
    </div>
  );
}
