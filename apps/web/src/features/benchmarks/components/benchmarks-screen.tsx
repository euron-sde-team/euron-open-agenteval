"use client";

import { AlertTriangleIcon, GitCompareIcon } from "lucide-react";
import * as React from "react";

import { Checkbox } from "@/components/ui/checkbox";
import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { PageHeader } from "@/components/page-header";
import { Surface, SurfaceHeader } from "@/components/surface";
import { Chip } from "@/components/ui/chip";
import { SimpleSelect } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useRuns } from "@/features/evaluations/api";
import { useActiveOrg } from "@/features/orgs/api";
import { deltaTone, formatDelta } from "@/lib/eval-status";
import { formatRelative } from "@/lib/format";

import { useBenchmarkCompare, useBenchmarkTrend } from "../api";
import { TrendChart } from "./trend-chart";

export function BenchmarksScreen() {
  const { org } = useActiveOrg();
  const orgId = org?.id ?? "";
  const runs = useRuns(orgId);
  const completedRuns = React.useMemo(
    () => (runs.data ?? []).filter((r) => r.status === "completed").sort((a, b) => a.created_at.localeCompare(b.created_at)),
    [runs.data],
  );

  const [baselineId, setBaselineId] = React.useState("");
  const [candidateId, setCandidateId] = React.useState("");
  const [trendRunIds, setTrendRunIds] = React.useState<string[]>([]);

  const compare = useBenchmarkCompare(orgId, baselineId || undefined, candidateId || undefined);
  // AC9: oldest first, regardless of the order the checkboxes were clicked in.
  const orderedTrendRunIds = React.useMemo(
    () => completedRuns.filter((r) => trendRunIds.includes(r.id)).map((r) => r.id),
    [completedRuns, trendRunIds],
  );
  const trend = useBenchmarkTrend(orgId, orderedTrendRunIds);

  function toggleTrendRun(id: string) {
    setTrendRunIds((prev) => (prev.includes(id) ? prev.filter((r) => r !== id) : [...prev, id]));
  }

  if (runs.isPending) {
    return null;
  }
  if (runs.isError) {
    return <ErrorState error={runs.error} onRetry={() => void runs.refetch()} />;
  }

  return (
    <>
      <PageHeader
        title="Benchmarks"
        description="Compare any two completed runs, or chart a metric's trend across several."
      />
      {completedRuns.length < 2 ? (
        <EmptyState
          icon={GitCompareIcon}
          title="Not enough completed runs yet"
          description="Benchmarking needs at least two completed evaluation runs of the same agent and dataset to compare."
        />
      ) : (
        <div className="flex flex-col gap-4">
          <Surface className="overflow-hidden">
            <SurfaceHeader title="Pairwise comparison" description="A regression is flagged automatically beyond the configured threshold (AC8)." />
            <div className="grid gap-3 px-5 pb-4 sm:grid-cols-2">
              <SimpleSelect
                value={baselineId}
                onValueChange={setBaselineId}
                placeholder="Baseline run"
                options={completedRuns.map((r) => ({ value: r.id, label: `${r.id.slice(0, 8)} (${formatRelative(r.created_at)})` }))}
              />
              <SimpleSelect
                value={candidateId}
                onValueChange={setCandidateId}
                placeholder="Candidate run"
                options={completedRuns.map((r) => ({ value: r.id, label: `${r.id.slice(0, 8)} (${formatRelative(r.created_at)})` }))}
              />
            </div>
            {baselineId && candidateId && baselineId === candidateId ? (
              <p className="px-5 pb-4 text-[13px] text-muted-foreground">Choose two different runs.</p>
            ) : compare.isError ? (
              <div className="px-5 pb-4">
                <ErrorState error={compare.error} onRetry={() => void compare.refetch()} compact />
              </div>
            ) : compare.data ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Metric</TableHead>
                    <TableHead>Baseline</TableHead>
                    <TableHead>Candidate</TableHead>
                    <TableHead>Delta</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {compare.data.deltas.map((d) => (
                    <TableRow key={d.metric_id}>
                      <TableCell className="font-medium text-foreground">{d.metric_id}</TableCell>
                      <TableCell className="tabular text-muted-foreground">{Math.round(d.baseline_mean * 100)}%</TableCell>
                      <TableCell className="tabular text-muted-foreground">{Math.round(d.candidate_mean * 100)}%</TableCell>
                      <TableCell>
                        <Chip tone={deltaTone(d.delta, d.is_regression)}>
                          {d.is_regression && <AlertTriangleIcon className="size-3" />}
                          {formatDelta(d.delta)}
                        </Chip>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <p className="px-5 pb-4 text-[13px] text-muted-foreground">Choose a baseline and a candidate run.</p>
            )}
          </Surface>

          <Surface className="p-5">
            <h2 className="mb-1 text-[13px] font-semibold text-foreground">Trend across runs</h2>
            <p className="mb-3 text-[13px] text-muted-foreground">Pick three or more runs to chart each metric over time (AC9).</p>
            <div className="mb-4 flex flex-wrap gap-x-4 gap-y-2">
              {completedRuns.map((r) => (
                <label key={r.id} className="flex items-center gap-1.5 text-[13px] text-foreground">
                  <Checkbox checked={trendRunIds.includes(r.id)} onCheckedChange={() => toggleTrendRun(r.id)} />
                  {r.id.slice(0, 8)}
                </label>
              ))}
            </div>
            {trendRunIds.length < 2 ? (
              <div className="flex h-56 items-center justify-center text-[13px] text-muted-foreground">
                Pick at least two runs.
              </div>
            ) : trend.isError ? (
              <ErrorState error={trend.error} onRetry={() => void trend.refetch()} compact />
            ) : trend.data ? (
              <TrendChart trend={trend.data} runOrder={orderedTrendRunIds} />
            ) : null}
          </Surface>
        </div>
      )}
    </>
  );
}
