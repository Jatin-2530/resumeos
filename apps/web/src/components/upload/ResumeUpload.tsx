"use client";

import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import toast from "react-hot-toast";
import { Upload, X, FileText, Loader2 } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

interface ResumeUploadProps {
  onClose: () => void;
  onSuccess: (resumeId: string) => void;
}

export default function ResumeUpload({ onClose, onSuccess }: ResumeUploadProps) {
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [uploading, setUploading] = useState(false);
  const queryClient = useQueryClient();

  const onDrop = useCallback((accepted: File[]) => {
    if (accepted[0]) {
      setFile(accepted[0]);
      if (!title) {
        setTitle(accepted[0].name.replace(/\.(docx|pdf)$/i, ""));
      }
    }
  }, [title]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
      "application/pdf": [".pdf"],
    },
    maxFiles: 1,
    maxSize: 10 * 1024 * 1024,
  });

  async function handleUpload() {
    if (!file) return;
    setUploading(true);
    const tid = toast.loading("Uploading resume…");
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("title", title || file.name);
      const { data } = await api.post("/resumes", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      toast.dismiss(tid);
      toast.success("Resume uploaded and parsed");
      queryClient.invalidateQueries({ queryKey: ["resumes"] });
      onSuccess(data.id);
    } catch (err: any) {
      toast.dismiss(tid);
      toast.error(err.response?.data?.detail || "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-modal w-full max-w-md animate-slide-up">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-surface-3">
          <h2 className="font-semibold text-ink-1">Upload Resume</h2>
          <button
            onClick={onClose}
            className="w-7 h-7 flex items-center justify-center rounded-lg hover:bg-surface-2 transition-colors"
          >
            <X className="w-4 h-4 text-ink-3" />
          </button>
        </div>

        <div className="p-6 space-y-4">
          {/* Drop zone */}
          <div
            {...getRootProps()}
            className={cn(
              "border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all",
              isDragActive
                ? "border-accent bg-accent-light"
                : file
                ? "border-success bg-success-light"
                : "border-surface-3 hover:border-accent-muted hover:bg-surface-1"
            )}
          >
            <input {...getInputProps()} />
            {file ? (
              <div className="flex flex-col items-center gap-2">
                <FileText className="w-8 h-8 text-success" />
                <p className="text-sm font-medium text-ink-1">{file.name}</p>
                <p className="text-xs text-ink-3">
                  {(file.size / 1024).toFixed(0)} KB
                </p>
                <button
                  type="button"
                  onClick={(e) => { e.stopPropagation(); setFile(null); }}
                  className="text-xs text-danger hover:underline mt-1"
                >
                  Remove
                </button>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-3">
                <div className="w-12 h-12 bg-surface-2 rounded-xl flex items-center justify-center">
                  <Upload className="w-5 h-5 text-ink-3" />
                </div>
                <div>
                  <p className="text-sm font-medium text-ink-1">
                    Drop your resume here
                  </p>
                  <p className="text-xs text-ink-3 mt-1">
                    DOCX or PDF · up to 10MB
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Title */}
          {file && (
            <div>
              <label className="block text-xs font-medium text-ink-2 mb-1.5">
                Resume title
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Marketing Manager Resume"
                className="w-full border border-surface-3 rounded-xl px-3 py-2.5 text-sm text-ink-1 focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent transition-colors"
              />
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3 pt-2">
            <button
              onClick={onClose}
              className="flex-1 border border-surface-3 text-sm text-ink-2 py-2.5 rounded-xl hover:bg-surface-1 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleUpload}
              disabled={!file || uploading}
              className="flex-1 flex items-center justify-center gap-2 bg-ink-1 text-white text-sm py-2.5 rounded-xl hover:bg-ink-2 disabled:opacity-50 transition-colors"
            >
              {uploading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                "Upload & Parse"
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
