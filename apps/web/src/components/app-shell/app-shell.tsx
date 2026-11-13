"use client";

import * as React from "react";

import { ErrorState } from "@/components/error-state";
import { EvalMark } from "@/components/eval-logo";
import { useMe } from "@/features/auth/api";
import { CreateOrgPrompt } from "@/features/orgs/components/create-org-prompt";
import { useActiveOrg, useOrgs } from "@/features/orgs/api";
import { isSessionExpired } from "@/lib/auth-redirect";

import { Sidebar } from "./sidebar";
import { Topbar } from "./topbar";

/**
 * Dashboard chrome plus the session gate: nothing behind it renders until /auth/me
 * confirms the session (a 401 redirects to /login from the query cache handler), and no
 * org-scoped screen renders until an active organization is resolved. A signed-in user
 * with no organization yet (a brand new self-hosted install) sees a prompt to create one
 * instead of an empty dashboard.
 */
export function AppShell({ children }: { children: React.ReactNode }) {
  const me = useMe();
  const orgs = useOrgs();
  const { org } = useActiveOrg();

  if (!me.data && me.isError && !isSessionExpired(me.error)) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-background p-4">
        <div className="surface w-full max-w-md">
          <ErrorState error={me.error} title="AgentEval is unreachable" onRetry={() => void me.refetch()} />
        </div>
      </div>
    );
  }

  if (!me.data || (me.data && orgs.isLoading)) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-background" aria-busy>
        <div className="flex flex-col items-center gap-3 text-muted-foreground">
          <EvalMark className="size-10 animate-pulse" />
          <span className="text-[13px]">{me.isError ? "Redirecting to sign in..." : "Loading AgentEval..."}</span>
        </div>
      </div>
    );
  }

  if (!org) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-background p-4">
        <div className="surface w-full max-w-md p-6">
          <CreateOrgPrompt />
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-dvh bg-background">
      <a
        href="#main"
        className="sr-only z-50 rounded-lg bg-card px-3 py-2 text-sm shadow-[var(--elev-3)] focus:not-sr-only focus:fixed focus:top-3 focus:left-3"
      >
        Skip to content
      </a>
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar />
        <main id="main" className="mx-auto w-full max-w-[1400px] flex-1 px-4 pt-4 pb-16 sm:px-6 lg:px-8">
          {children}
        </main>
      </div>
    </div>
  );
}
