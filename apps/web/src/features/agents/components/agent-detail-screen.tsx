"use client";

import { ArrowLeftIcon, GitBranchIcon, PlusIcon } from "lucide-react";
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
import { adapterTypeLabel } from "@/lib/eval-status";
import { formatRelative } from "@/lib/format";

import { useAgent, useAgentVersions } from "../api";
import { CreateVersionDialog } from "./create-version-dialog";

export function AgentDetailScreen({ agentId }: { agentId: string }) {
  const { org } = useActiveOrg();
  const orgId = org?.id ?? "";
  const { isMember } = useOrgPermissions();
  const agent = useAgent(orgId, agentId);
  const versions = useAgentVersions(orgId, agentId);
  const [versionOpen, setVersionOpen] = React.useState(false);

  if (agent.isPending) {
    return <TableSkeleton rows={4} cols={2} />;
  }
  if (!agent.data) {
    return (
      <EmptyState
        icon={GitBranchIcon}
        title="Agent not found"
        description="It may have been removed, or belongs to a different organization."
      />
    );
  }

  return (
    <>
      <Link href="/agents" className="mb-3 inline-flex items-center gap-1.5 text-[13px] text-muted-foreground hover:text-foreground">
        <ArrowLeftIcon className="size-3.5" />
        Agents
      </Link>
      <PageHeader
        title={agent.data.name}
        description={`${adapterTypeLabel(agent.data.adapter_type)} agent, ${agent.data.provider} provider.`}
        actions={
          isMember && versions.data?.length !== 0 && (
            <Button onClick={() => setVersionOpen(true)}>
              <PlusIcon />
              New version
            </Button>
          )
        }
      />
      <Surface className="overflow-hidden">
        {versions.isPending ? (
          <TableSkeleton rows={3} cols={3} />
        ) : versions.isError ? (
          <ErrorState error={versions.error} onRetry={() => void versions.refetch()} />
        ) : versions.data.length === 0 ? (
          <EmptyState
            icon={GitBranchIcon}
            title="No versions yet"
            description="Create a version to run this agent against a dataset. A benchmark compares specific versions, never just whatever is latest."
            action={
              isMember && (
                <Button onClick={() => setVersionOpen(true)}>
                  <PlusIcon />
                  New version
                </Button>
              )
            }
          />
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Version</TableHead>
                <TableHead>Config</TableHead>
                <TableHead>Created</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {versions.data
                .slice()
                .sort((a, b) => b.created_at.localeCompare(a.created_at))
                .map((version) => (
                  <TableRow key={version.id}>
                    <TableCell>
                      <Chip tone="primary">{version.label}</Chip>
                    </TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">
                      {Object.keys(version.config).length === 0
                        ? "None"
                        : Object.entries(version.config)
                            .map(([k, v]) => `${k}=${String(v)}`)
                            .join(", ")}
                    </TableCell>
                    <TableCell className="text-muted-foreground">{formatRelative(version.created_at)}</TableCell>
                  </TableRow>
                ))}
            </TableBody>
          </Table>
        )}
      </Surface>
      <CreateVersionDialog orgId={orgId} agent={agent.data} open={versionOpen} onOpenChange={setVersionOpen} />
    </>
  );
}
