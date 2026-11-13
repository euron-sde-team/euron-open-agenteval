"use client";

import { DatabaseIcon, PlusIcon } from "lucide-react";
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
import { formatRelative } from "@/lib/format";

import { useDatasets } from "../api";
import { CreateDatasetDialog } from "./create-dataset-dialog";

export function DatasetsScreen() {
  const { org } = useActiveOrg();
  const orgId = org?.id ?? "";
  const { isMember } = useOrgPermissions();
  const datasets = useDatasets(orgId);
  const [createOpen, setCreateOpen] = React.useState(false);

  return (
    <>
      <PageHeader
        title="Datasets"
        description="Versioned collections of test cases. Editing one creates a new version; past runs keep the version they ran against."
        actions={
          isMember && datasets.data?.length !== 0 && (
            <Button onClick={() => setCreateOpen(true)}>
              <PlusIcon />
              Create dataset
            </Button>
          )
        }
      />
      <Surface className="overflow-hidden">
        {datasets.isPending ? (
          <TableSkeleton rows={5} cols={3} />
        ) : datasets.isError ? (
          <ErrorState error={datasets.error} onRetry={() => void datasets.refetch()} />
        ) : datasets.data.length === 0 ? (
          <EmptyState
            icon={DatabaseIcon}
            title="No datasets yet"
            description="Create a dataset of test cases, each with an expected behavior, to run an agent against."
            action={
              isMember && (
                <Button onClick={() => setCreateOpen(true)}>
                  <PlusIcon />
                  Create dataset
                </Button>
              )
            }
          />
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Dataset</TableHead>
                <TableHead>Version</TableHead>
                <TableHead>Test cases</TableHead>
                <TableHead>Created</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {datasets.data.map((dataset) => (
                <TableRow key={dataset.id}>
                  <TableCell>
                    <Link href={`/datasets/${dataset.id}`} className="font-medium text-foreground hover:underline">
                      {dataset.name}
                    </Link>
                  </TableCell>
                  <TableCell>
                    <Chip tone="primary">v{dataset.current_version_number}</Chip>
                  </TableCell>
                  <TableCell className="text-muted-foreground">{dataset.test_case_count}</TableCell>
                  <TableCell className="text-muted-foreground">{formatRelative(dataset.created_at)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Surface>
      <CreateDatasetDialog orgId={orgId} open={createOpen} onOpenChange={setCreateOpen} />
    </>
  );
}
