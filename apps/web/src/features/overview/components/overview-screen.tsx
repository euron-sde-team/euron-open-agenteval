"use client";

import { BotIcon, DatabaseIcon, FlaskConicalIcon, KeyRoundIcon } from "lucide-react";
import Link from "next/link";
import * as React from "react";

import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { PageHeader } from "@/components/page-header";
import { StatTile } from "@/components/stat-tile";
import { buttonVariants } from "@/components/ui/button";
import { Chip } from "@/components/ui/chip";
import { useAgents } from "@/features/agents/api";
import { useDatasets } from "@/features/datasets/api";
import { useRun, useRuns } from "@/features/evaluations/api";
import { useActiveOrg } from "@/features/orgs/api";
import { runStatusLabel, runStatusTone } from "@/lib/eval-status";
import { formatRelative } from "@/lib/format";

import { MetricChart } from "./metric-chart";

export function OverviewScreen() {
  const { org } = useActiveOrg();
  const orgId = org?.id ?? "";
  const agents = useAgents(orgId);
  const datasets = useDatasets(orgId);
  const runs = useRuns(orgId);

  const allRuns = runs.data ?? [];
  const recentRuns = allRuns.slice().sort((a, b) => b.created_at.localeCompare(a.created_at)).slice(0, 8);
  const latestCompleted = allRuns
    .slice()
    .filter((r) => r.status === "completed")
    .sort((a, b) => b.created_at.localeCompare(a.created_at))[0];

  return (
    <>
      <PageHeader
        title="Overview"
        description="Every agent you register, every run it scores, in one place."
        actions={
          <Link href="/agents" className={buttonVariants({ variant: "outline", size: "sm" })}>
            Register an agent
          </Link>
        }
      />
      <div className="flex flex-col gap-4">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatTile
            label="Agents"
            value={agents.isPending ? "" : (agents.data?.length ?? 0)}
            loading={agents.isPending}
            icon={BotIcon}
            caption="Registered in this organization"
          />
          <StatTile
            label="Datasets"
            value={datasets.isPending ? "" : (datasets.data?.length ?? 0)}
            loading={datasets.isPending}
            icon={DatabaseIcon}
            caption="Versioned test-case collections"
          />
          <StatTile
            label="Evaluation runs"
            value={runs.isPending ? "" : allRuns.length}
            loading={runs.isPending}
            icon={FlaskConicalIcon}
            caption="Across every agent and dataset"
          />
          <StatTile
            label="API keys"
            value={<Link href="/settings" className="hover:underline">Manage</Link>}
            icon={KeyRoundIcon}
            caption="For the AgentEval SDK and CI"
          />
        </div>

        <div className="grid gap-4 lg:grid-cols-3">
          <div className="surface lg:col-span-2 p-5">
            <h2 className="text-[13px] font-semibold text-foreground">
              Latest run's metrics
              {latestCompleted && (
                <span className="ml-2 font-normal text-muted-foreground">
                  ({formatRelative(latestCompleted.finished_at)})
                </span>
              )}
            </h2>
            {runs.isError ? (
              <ErrorState error={runs.error} onRetry={() => void runs.refetch()} compact />
            ) : !latestCompleted ? (
              <div className="flex h-56 items-center justify-center text-[13px] text-muted-foreground">
                No completed run yet.
              </div>
            ) : (
              <MetricChartForRun orgId={orgId} runId={latestCompleted.id} />
            )}
          </div>
          <div className="surface p-5">
            <h2 className="mb-3 text-[13px] font-semibold text-foreground">Recent runs</h2>
            {runs.isError ? (
              <ErrorState error={runs.error} onRetry={() => void runs.refetch()} compact />
            ) : recentRuns.length === 0 ? (
              <EmptyState
                icon={FlaskConicalIcon}
                title="No runs yet"
                description="Register an agent and queue a run to see it here."
                compact
              />
            ) : (
              <ul className="space-y-2.5">
                {recentRuns.map((run) => (
                  <li key={run.id}>
                    <Link
                      href={`/evaluations/${run.id}`}
                      className="flex items-center justify-between gap-2 rounded-lg px-1.5 py-1 text-[13px] transition-colors hover:bg-accent/60"
                    >
                      <span className="min-w-0 truncate text-foreground">{run.id.slice(0, 8)}</span>
                      <Chip tone={runStatusTone(run.status)}>{runStatusLabel(run.status)}</Chip>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>
    </>
  );
}

function MetricChartForRun({ orgId, runId }: { orgId: string; runId: string }) {
  const run = useRun(orgId, runId);
  return <MetricChart results={run.data?.results ?? []} />;
}
