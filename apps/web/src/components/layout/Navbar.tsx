"use client";

import Link from "next/link";
import { FileText } from "lucide-react";

export default function Navbar() {
  return (
    <nav className="fixed top-0 left-0 right-0 z-40 bg-white/90 backdrop-blur border-b border-surface-3 h-14">
      <div className="max-w-7xl mx-auto px-6 h-full flex items-center justify-between">
        <Link
          href="/dashboard"
          className="flex items-center gap-2 font-semibold text-ink-1"
        >
          <div className="w-7 h-7 bg-ink-1 rounded-lg flex items-center justify-center">
            <FileText className="w-3.5 h-3.5 text-white" />
          </div>
          Resume<span className="text-accent">OS</span>
        </Link>
      </div>
    </nav>
  );
}
