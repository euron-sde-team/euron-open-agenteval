"use client";

import { FlaskConicalIcon, PlusIcon } from "lucide-react";
import Link from "next/link";
import * as React from "react";

import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { PageHeader } from "@/components/page-header";
import { Surface } from "@/components/surface";
import { TableSkeleton } from "@/components/table-skeleton";
import { Button } from "@/components/ui/button";
import { Chip } from "@/components/ui/chip";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useActiveOrg, useOrgPermissions } from "@/features/orgs/api";
import { runStatusLabel, runStatusTone } from "@/lib/eval-status";
import { formatRelative } from "@/lib/format";

import { useRuns } from "../api";
import { QueueRunDialog } from "./queue-run-dialog";

export function EvaluationsScreen() {
  const { org } = useActiveOrg();
  const orgId = org?.id ?? "";
  const { isMember } = useOrgPermissions();
  const runs = useRuns(orgId);
  const [queueOpen, setQueueOpen] = React.useState(false);

  return (
    <>
      <PageHeader
        title="Evaluations"
        description="Run an agent version against a dataset, then inspect each test case's score and trace."
        actions={
          isMember && runs.data?.length !== 0 && (
            <Button onClick={() => setQueueOpen(true)}>
              <PlusIcon />
              Queue run
            </Button>
          )
        }
      />
      <Surface className="overflow-hidden">
        {runs.isPending ? (
          <TableSkeleton rows={5} cols={4} />
        ) : runs.isError ? (
          <ErrorState error={runs.error} onRetry={() => void runs.refetch()} />
        ) : runs.data.length === 0 ? (
          <EmptyState
            icon={FlaskConicalIcon}
            title="No evaluation runs yet"
            description="Queue a run against a registered agent version and a dataset to see its results here."
            action={
              isMember && (
                <Button onClick={() => setQueueOpen(true)}>
                  <PlusIcon />
                  Queue run
                </Button>
              )
            }
          />
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Run</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Metrics</TableHead>
                <TableHead>Created</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {runs.data
                .slice()
                .sort((a, b) => b.created_at.localeCompare(a.created_at))
                .map((run) => (
                  <TableRow key={run.id}>
                    <TableCell>
                      <Link href={`/evaluations/${run.id}`} className="font-mono text-[13px] font-medium text-foreground hover:underline">
                        {run.id.slice(0, 8)}
                      </Link>
                    </TableCell>
                    <TableCell>
                      <Chip tone={runStatusTone(run.status)}>{runStatusLabel(run.status)}</Chip>
                    </TableCell>
                    <TableCell className="text-muted-foreground">{run.metric_ids.join(", ")}</TableCell>
                    <TableCell className="text-muted-foreground">{formatRelative(run.created_at)}</TableCell>
                  </TableRow>
                ))}
            </TableBody>
          </Table>
        )}
      </Surface>
      <QueueRunDialog orgId={orgId} open={queueOpen} onOpenChange={setQueueOpen} />
    </>
  );
}
