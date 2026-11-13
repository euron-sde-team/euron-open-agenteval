"use client";

import { ScrollTextIcon } from "lucide-react";

import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { PageHeader } from "@/components/page-header";
import { Surface } from "@/components/surface";
import { TableSkeleton } from "@/components/table-skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useActiveOrg } from "@/features/orgs/api";
import { formatDateTime } from "@/lib/format";

import { useAuditLog } from "../api";

export function AuditScreen() {
  const { org } = useActiveOrg();
  const orgId = org?.id ?? "";
  const audit = useAuditLog(orgId);

  return (
    <>
      <PageHeader
        title="Audit log"
        description="Every evaluation run and every judge-call reveal in this organization, append only, newest first."
      />
      <Surface className="overflow-hidden">
        {audit.isPending ? (
          <TableSkeleton rows={8} cols={4} />
        ) : audit.isError ? (
          <ErrorState error={audit.error} onRetry={() => void audit.refetch()} />
        ) : audit.data.length === 0 ? (
          <EmptyState icon={ScrollTextIcon} title="Nothing logged yet" description="Actions will appear here as they happen." />
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>When</TableHead>
                <TableHead>Who</TableHead>
                <TableHead>Action</TableHead>
                <TableHead>Target</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {audit.data.map((entry) => (
                <TableRow key={entry.id}>
                  <TableCell className="text-muted-foreground">{formatDateTime(entry.at)}</TableCell>
                  <TableCell className="text-foreground">{entry.actor_email ?? "System"}</TableCell>
                  <TableCell className="font-mono text-[12.5px] text-foreground">{entry.action}</TableCell>
                  <TableCell className="text-muted-foreground">
                    {entry.target_type ? `${entry.target_type} ${entry.target_id ?? ""}`.trim() : "n/a"}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Surface>
    </>
  );
}
