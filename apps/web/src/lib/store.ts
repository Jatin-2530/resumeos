import { create } from "zustand";
import { persist } from "zustand/middleware";

interface UIState {
  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
  toggleSidebar: () => void;
}

interface ResumeEditorState {
  activeResumeId: string | null;
  activeJDId: string | null;
  setActiveResume: (id: string | null) => void;
  setActiveJD: (id: string | null) => void;
  selectedBulletId: string | null;
  setSelectedBullet: (id: string | null) => void;
}

type AppStore = UIState & ResumeEditorState;

export const useAppStore = create<AppStore>()(
  persist(
    (set) => ({
      // UI
      sidebarOpen: true,
      setSidebarOpen: (open) => set({ sidebarOpen: open }),
      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),

      // Resume editor
      activeResumeId: null,
      activeJDId: null,
      setActiveResume: (id) => set({ activeResumeId: id }),
      setActiveJD: (id) => set({ activeJDId: id }),
      selectedBulletId: null,
      setSelectedBullet: (id) => set({ selectedBulletId: id }),
    }),
    {
      name: "resumeos-ui",
      partialize: (state) => ({
        activeJDId: state.activeJDId,
      }),
    }
  )
);
