"use client";

import { DownloadIcon, FileJsonIcon, FileTextIcon } from "lucide-react";
import * as React from "react";

import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { PageHeader } from "@/components/page-header";
import { Surface, SurfaceHeader } from "@/components/surface";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useRuns } from "@/features/evaluations/api";
import { useActiveOrg } from "@/features/orgs/api";
import type { EvaluationRun } from "@/lib/api/types";

/**
 * There is no server-side export endpoint (apps/api/src/agenteval has no `reports`
 * domain at all, despite docs/PLAN.md's screens list naming one): this builds a CSV or
 * JSON report in the browser from the evaluation runs already fetched for this
 * organization, rather than inventing a fake export endpoint that does not exist. A
 * per-run export omits judge raw responses and prompts on purpose; those stay behind
 * the explicit, audited reveal on the run detail screen, never bundled into a bulk file.
 */
function downloadBlob(filename: string, content: string, type: string) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function toCsv(runs: EvaluationRun[]): string {
  const headers = ["run_id", "status", "metric_ids", "started_at", "finished_at", "error", "created_at"];
  const rows = runs.map((r) =>
    [r.id, r.status, r.metric_ids.join(" "), r.started_at ?? "", r.finished_at ?? "", r.error ?? "", r.created_at]
      .map((v) => `"${v.replace(/"/g, '""')}"`)
      .join(","),
  );
  return [headers.join(","), ...rows].join("\n");
}

export function ReportsScreen() {
  const { org } = useActiveOrg();
  const orgId = org?.id ?? "";
  const runs = useRuns(orgId);

  function exportCsv() {
    if (!runs.data) return;
    downloadBlob(`agenteval-runs-${org?.slug ?? "export"}.csv`, toCsv(runs.data), "text/csv");
  }

  function exportJson() {
    if (!runs.data) return;
    downloadBlob(`agenteval-runs-${org?.slug ?? "export"}.json`, JSON.stringify(runs.data, null, 2), "application/json");
  }

  return (
    <>
      <PageHeader
        title="Reports"
        description="Export every evaluation run this organization has, for a ticket, an audit or a spreadsheet. No server-side export exists yet, so this is built from what the dashboard already fetched."
      />
      <Surface className="p-5">
        <SurfaceHeader
          title="Evaluation runs export"
          description={runs.data ? `${runs.data.length} run(s) across every agent and dataset.` : undefined}
        />
        {runs.isPending ? (
          <Skeleton className="mx-5 mb-4 h-9 w-48" />
        ) : runs.isError ? (
          <div className="px-5 pb-4">
            <ErrorState error={runs.error} onRetry={() => void runs.refetch()} compact />
          </div>
        ) : runs.data.length === 0 ? (
          <div className="px-5 pb-4">
            <EmptyState icon={FileTextIcon} title="Nothing to export yet" description="Queue a run first." compact />
          </div>
        ) : (
          <div className="flex flex-wrap gap-2 px-5 pb-4">
            <Button variant="outline" onClick={exportCsv}>
              <DownloadIcon />
              Export CSV
            </Button>
            <Button variant="outline" onClick={exportJson}>
              <FileJsonIcon />
              Export JSON
            </Button>
          </div>
        )}
      </Surface>
    </>
  );
}
