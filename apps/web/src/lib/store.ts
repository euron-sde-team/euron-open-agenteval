"use client";

import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

/**
 * Persisted UI preferences only (never server data). Rehydrated after mount so the
 * first client render matches the server render. The theme itself is persisted by
 * next-themes. The active organization id is the one piece of "server-ish" state kept
 * here: a user can belong to more than one organization, and every list in the product
 * is scoped under one org id, so the whole app needs a single source of truth for which
 * one is current.
 */
interface UiPrefs {
  activeOrgId: string | null;
  sidebarCollapsed: boolean;
  setActiveOrgId: (id: string | null) => void;
  toggleSidebar: () => void;
}

export const useUiPrefs = create<UiPrefs>()(
  persist(
    (set) => ({
      activeOrgId: null,
      sidebarCollapsed: false,
      setActiveOrgId: (activeOrgId) => set({ activeOrgId }),
      toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
    }),
    {
      name: "agenteval.ui",
      version: 1,
      skipHydration: true,
      storage: createJSONStorage(() => localStorage),
      partialize: (s) => ({ activeOrgId: s.activeOrgId, sidebarCollapsed: s.sidebarCollapsed }),
      merge: (persisted, current) => {
        const p = (persisted ?? {}) as Partial<UiPrefs>;
        return {
          ...current,
          activeOrgId: typeof p.activeOrgId === "string" ? p.activeOrgId : current.activeOrgId,
          sidebarCollapsed:
            typeof p.sidebarCollapsed === "boolean" ? p.sidebarCollapsed : current.sidebarCollapsed,
        };
      },
    },
  ),
);
