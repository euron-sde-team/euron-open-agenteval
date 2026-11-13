"use client";

import * as React from "react";

import { Chip } from "@/components/ui/chip";
import type { Span } from "@/lib/api/types";

/**
 * A minimal waterfall: every span as a row, indented by its parent/child depth, with
 * its own gen_ai.* attributes shown on click. Durations in this product's own spans
 * are typically sub-millisecond for a mock agent, so the bar is a relative-position
 * indicator (start offset within the trace), not a meaningfully scaled duration chart.
 */
export function SpanWaterfall({ spans }: { spans: Span[] }) {
  const [openId, setOpenId] = React.useState<string | null>(null);

  const ordered = React.useMemo(() => {
    const byParent = new Map<string | null, Span[]>();
    for (const span of spans) {
      const key = span.parent_otel_span_id ?? null;
      const list = byParent.get(key) ?? [];
      list.push(span);
      byParent.set(key, list);
    }
    const out: { span: Span; depth: number }[] = [];
    function walk(parentId: string | null, depth: number) {
      for (const span of byParent.get(parentId) ?? []) {
        out.push({ span, depth });
        walk(span.otel_span_id, depth + 1);
      }
    }
    walk(null, 0);
    return out;
  }, [spans]);

  if (spans.length === 0) {
    return <p className="px-5 py-8 text-center text-[13px] text-muted-foreground">No spans recorded.</p>;
  }

  return (
    <ul className="divide-y divide-hairline">
      {ordered.map(({ span, depth }) => {
        const open = openId === span.id;
        return (
          <li key={span.id}>
            <button
              type="button"
              onClick={() => setOpenId(open ? null : span.id)}
              className="flex w-full items-center gap-2 px-5 py-2.5 text-left transition-colors hover:bg-accent/40"
              style={{ paddingLeft: `${20 + depth * 20}px` }}
            >
              <Chip tone={span.status === "ok" ? "savings" : "danger"}>{span.gen_ai_operation_name ?? "span"}</Chip>
              <span className="min-w-0 flex-1 truncate font-mono text-[12.5px] text-foreground">{span.name}</span>
              <span className="shrink-0 text-[11.5px] text-faint">{span.otel_span_id}</span>
            </button>
            {open && (
              <pre className="mx-5 mb-3 overflow-x-auto rounded-lg bg-muted px-3 py-2 font-mono text-[11.5px] text-muted-foreground">
                {JSON.stringify(span.attributes, null, 2)}
              </pre>
            )}
          </li>
        );
      })}
    </ul>
  );
}
