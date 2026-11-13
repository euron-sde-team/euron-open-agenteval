"use client";

import { ArrowLeftIcon, WaypointsIcon } from "lucide-react";
import Link from "next/link";

import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { Surface } from "@/components/surface";
import { TableSkeleton } from "@/components/table-skeleton";
import { useActiveOrg } from "@/features/orgs/api";
import { formatDateTime } from "@/lib/format";

import { useTrace } from "../api";
import { SpanWaterfall } from "./span-waterfall";

export function TraceDetailScreen({ traceId }: { traceId: string }) {
  const { org } = useActiveOrg();
  const orgId = org?.id ?? "";
  const trace = useTrace(orgId, traceId);

  if (trace.isPending) {
    return <TableSkeleton rows={4} cols={1} />;
  }
  if (!trace.data) {
    return (
      <EmptyState
        icon={WaypointsIcon}
        title="Trace not found"
        description="It may have been removed, belongs to a different organization, or the id was mistyped."
      />
    );
  }

  return (
    <>
      <Link href="/traces" className="mb-3 inline-flex items-center gap-1.5 text-[13px] text-muted-foreground hover:text-foreground">
        <ArrowLeftIcon className="size-3.5" />
        Execution traces
      </Link>
      <PageHeader
        title={`Trace ${trace.data.otel_trace_id.slice(0, 12)}`}
        description={`${trace.data.spans.length} span(s), captured ${formatDateTime(trace.data.created_at)}.`}
      />
      <Surface className="overflow-hidden">
        <SpanWaterfall spans={trace.data.spans} />
      </Surface>
    </>
  );
}
