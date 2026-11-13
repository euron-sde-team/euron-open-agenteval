"use client";

import { AlertTriangleIcon, ArrowLeftIcon, FlaskConicalIcon, WaypointsIcon } from "lucide-react";
import Link from "next/link";
import * as React from "react";
import { toast } from "sonner";

import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { Surface } from "@/components/surface";
import { Button } from "@/components/ui/button";
import { Chip } from "@/components/ui/chip";
import { TableSkeleton } from "@/components/table-skeleton";
import { useActiveOrg } from "@/features/orgs/api";
import { useTraceForRunAndCase } from "@/features/traces/api";
import { errorMessage } from "@/lib/api/errors";
import { methodLabel, resultTone, runStatusLabel, runStatusTone, scorePercent } from "@/lib/eval-status";
import { formatDateTime } from "@/lib/format";

import { useActivateRun, useRun } from "../api";
import { JudgeCallReveal } from "./judge-call-reveal";

function ResultRow({ orgId, runId, result }: { orgId: string; runId: string; result: { id: string; test_case_id: string; metric_id: string; method: string; score: number; passed: boolean; reasoning: string; same_family_warning: boolean } }) {
  const [expanded, setExpanded] = React.useState(false);
  const trace = useTraceForRunAndCase(orgId, expanded ? runId : undefined, result.test_case_id);

  return (
    <li className="px-5 py-3.5">
      <button type="button" className="flex w-full items-center justify-between gap-3 text-left" onClick={() => setExpanded((e) => !e)}>
        <div className="flex min-w-0 items-center gap-2">
          <Chip tone={resultTone(result.passed)}>{result.passed ? "Passed" : "Failed"}</Chip>
          <span className="truncate text-[13px] font-medium text-foreground">{result.metric_id}</span>
          <Chip tone="primary">{methodLabel(result.method)}</Chip>
          {result.same_family_warning && (
            <span title="The judge shares a provider family with the agent under test; self-preference bias is a known risk here.">
              <Chip tone="warning">
                <AlertTriangleIcon className="size-3" />
                Same-family judge
              </Chip>
            </span>
          )}
        </div>
        <span className="shrink-0 text-[13px] font-semibold text-foreground tabular">{scorePercent(result.score)}</span>
      </button>
      {expanded && (
        <div className="mt-3 space-y-3 border-t border-hairline pt-3">
          {result.reasoning && <p className="text-[13px] text-muted-foreground">{result.reasoning}</p>}
          {result.method === "judge" && <JudgeCallReveal orgId={orgId} resultId={result.id} />}
          {trace.data ? (
            <Link
              href={`/traces/${trace.data.id}`}
              className="inline-flex items-center gap-1.5 text-[13px] text-primary hover:underline"
            >
              <WaypointsIcon className="size-3.5" />
              View the execution trace for this test case
            </Link>
          ) : trace.isError ? (
            <p className="text-[13px] text-muted-foreground">No trace was recorded for this test case.</p>
          ) : null}
        </div>
      )}
    </li>
  );
}

export function RunDetailScreen({ runId }: { runId: string }) {
  const { org } = useActiveOrg();
  const orgId = org?.id ?? "";
  const run = useRun(orgId, runId);
  const activate = useActivateRun(orgId);

  if (run.isPending) {
    return <TableSkeleton rows={4} cols={1} />;
  }
  if (!run.data) {
    return (
      <EmptyState
        icon={FlaskConicalIcon}
        title="Run not found"
        description="It may have been removed, or belongs to a different organization."
      />
    );
  }

  const { data } = run;
  const results = data.results ?? [];

  return (
    <>
      <Link href="/evaluations" className="mb-3 inline-flex items-center gap-1.5 text-[13px] text-muted-foreground hover:text-foreground">
        <ArrowLeftIcon className="size-3.5" />
        Evaluations
      </Link>
      <PageHeader
        title={`Run ${data.id.slice(0, 8)}`}
        description={formatDateTime(data.created_at)}
        eyebrow={<Chip tone={runStatusTone(data.status)}>{runStatusLabel(data.status)}</Chip>}
        actions={
          data.status === "pending_traces" && (
            <Button
              onClick={() =>
                activate.mutate(runId, {
                  onSuccess: () => toast.success("Run activated; the worker will pick it up shortly."),
                  onError: (err) => toast.error(errorMessage(err)),
                })
              }
              disabled={activate.isPending}
            >
              {activate.isPending ? "Activating..." : "Activate (traces pushed)"}
            </Button>
          )
        }
      />
      {data.status === "pending_traces" && (
        <div className="mb-4 rounded-lg bg-warning-soft px-3.5 py-2.5 text-[13px] text-warning">
          This run uses a recorded agent: it waits for the SDK to push every test case's trace, then needs an
          explicit activate before a worker can score it.
        </div>
      )}
      {data.error && (
        <div className="mb-4 rounded-lg bg-danger-soft px-3.5 py-2.5 text-[13px] text-danger">{data.error}</div>
      )}
      <Surface className="overflow-hidden">
        {results.length === 0 ? (
          <EmptyState
            icon={FlaskConicalIcon}
            title="No results yet"
            description={data.status === "completed" ? "This run finished with no results." : "Results appear here once the run completes."}
          />
        ) : (
          <ul className="divide-y divide-hairline">
            {results.map((result) => (
              <ResultRow key={result.id} orgId={orgId} runId={runId} result={result} />
            ))}
          </ul>
        )}
      </Surface>
    </>
  );
}
