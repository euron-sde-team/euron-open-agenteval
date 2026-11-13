"use client";

import { useId } from "react";

import { cn } from "@/lib/cn";

/** The AgentEval mark: a gauge needle landing on a check, scoring made visible in one glyph. */
export function EvalMark({ className }: { className?: string }) {
  // A unique gradient id per instance: when the first SVG defining a shared id sits in a
  // hidden subtree (the collapsed sidebar on phones), browsers resolve the fill to nothing.
  const gradient = `ae-mark-${useId().replace(/:/g, "")}`;
  return (
    <svg viewBox="0 0 32 32" aria-hidden className={cn("size-7 shrink-0", className)}>
      <defs>
        <linearGradient id={gradient} x1="4" y1="4" x2="28" y2="28" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="var(--chart-spend)" />
          <stop offset="1" stopColor="var(--primary)" />
        </linearGradient>
      </defs>
      <circle cx="16" cy="16" r="13.5" fill={`url(#${gradient})`} />
      <path
        d="M9 17.5 13.5 22 23 10.5"
        fill="none"
        stroke="white"
        strokeWidth="2.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function EvalLogo({ className, collapsed = false }: { className?: string; collapsed?: boolean }) {
  return (
    <span className={cn("inline-flex items-center gap-2.5", className)}>
      <EvalMark />
      {!collapsed && (
        <span className="text-[15px] font-semibold tracking-[-0.02em] text-foreground">AgentEval</span>
      )}
    </span>
  );
}
