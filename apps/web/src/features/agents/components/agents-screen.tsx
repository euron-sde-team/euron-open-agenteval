"use client";

import { BotIcon, PlusIcon } from "lucide-react";
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

import { useAgents } from "../api";
import { RegisterAgentDialog } from "./register-agent-dialog";

export function AgentsScreen() {
  const { org } = useActiveOrg();
  const orgId = org?.id ?? "";
  const { isMember } = useOrgPermissions();
  const agents = useAgents(orgId);
  const [registerOpen, setRegisterOpen] = React.useState(false);

  return (
    <>
      <PageHeader
        title="Agents"
        description="Every agent AgentEval can score. Register one, then add a version each time it changes."
        actions={
          isMember && agents.data?.length !== 0 && (
            <Button onClick={() => setRegisterOpen(true)}>
              <PlusIcon />
              Register agent
            </Button>
          )
        }
      />
      <Surface className="overflow-hidden">
        {agents.isPending ? (
          <TableSkeleton rows={5} cols={4} />
        ) : agents.isError ? (
          <ErrorState error={agents.error} onRetry={() => void agents.refetch()} />
        ) : agents.data.length === 0 ? (
          <EmptyState
            icon={BotIcon}
            title="No agents registered"
            description="Register an agent, give it a version, then run it against a dataset to see its first score."
            action={
              isMember && (
                <Button onClick={() => setRegisterOpen(true)}>
                  <PlusIcon />
                  Register agent
                </Button>
              )
            }
          />
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Agent</TableHead>
                <TableHead>Adapter</TableHead>
                <TableHead>Provider</TableHead>
                <TableHead>Registered</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {agents.data.map((agent) => (
                <TableRow key={agent.id}>
                  <TableCell>
                    <Link href={`/agents/${agent.id}`} className="font-medium text-foreground hover:underline">
                      {agent.name}
                    </Link>
                  </TableCell>
                  <TableCell>
                    <Chip tone="primary">{adapterTypeLabel(agent.adapter_type)}</Chip>
                  </TableCell>
                  <TableCell className="capitalize text-muted-foreground">{agent.provider}</TableCell>
                  <TableCell className="text-muted-foreground">{formatRelative(agent.created_at)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Surface>
      <RegisterAgentDialog orgId={orgId} open={registerOpen} onOpenChange={setRegisterOpen} />
    </>
  );
}
