"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FileText, LogOut, User } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import type { User as SupabaseUser } from "@supabase/supabase-js";

interface NavbarProps {
  user: SupabaseUser;
}

export default function Navbar({ user }: NavbarProps) {
  const router = useRouter();
  const supabase = createClient();

  async function handleSignOut() {
    await supabase.auth.signOut();
    router.push("/login");
  }

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

        <div className="flex items-center gap-2">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl text-sm text-ink-3">
            <div className="w-6 h-6 bg-accent-light rounded-full flex items-center justify-center">
              <User className="w-3 h-3 text-accent" />
            </div>
            <span className="hidden sm:block text-xs">{user.email}</span>
          </div>
          <button
            onClick={handleSignOut}
            className="w-8 h-8 flex items-center justify-center rounded-xl hover:bg-surface-2 transition-colors text-ink-4 hover:text-ink-2"
            title="Sign out"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </nav>
  );
}
