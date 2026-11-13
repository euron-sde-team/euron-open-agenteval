"use client";

import { ArrowLeftIcon, ClipboardListIcon, PencilIcon } from "lucide-react";
import Link from "next/link";
import * as React from "react";

import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { PageHeader } from "@/components/page-header";
import { Surface } from "@/components/surface";
import { TableSkeleton } from "@/components/table-skeleton";
import { Button } from "@/components/ui/button";
import { Chip } from "@/components/ui/chip";
import { useOrgPermissions, useActiveOrg } from "@/features/orgs/api";

import { useDataset, useTestCases } from "../api";
import { CreateDatasetVersionDialog } from "./create-dataset-version-dialog";

export function DatasetDetailScreen({ datasetId }: { datasetId: string }) {
  const { org } = useActiveOrg();
  const orgId = org?.id ?? "";
  const { isMember } = useOrgPermissions();
  const dataset = useDataset(orgId, datasetId);
  const testCases = useTestCases(orgId, datasetId);
  const [versionOpen, setVersionOpen] = React.useState(false);

  if (dataset.isPending) {
    return <TableSkeleton rows={4} cols={2} />;
  }
  if (!dataset.data) {
    return (
      <EmptyState
        icon={ClipboardListIcon}
        title="Dataset not found"
        description="It may have been removed, or belongs to a different organization."
      />
    );
  }

  return (
    <>
      <Link href="/datasets" className="mb-3 inline-flex items-center gap-1.5 text-[13px] text-muted-foreground hover:text-foreground">
        <ArrowLeftIcon className="size-3.5" />
        Datasets
      </Link>
      <PageHeader
        title={dataset.data.name}
        description={`Version ${dataset.data.current_version_number}, ${dataset.data.test_case_count} test case(s). Editing creates a new version.`}
        actions={
          isMember && (
            <Button variant="outline" onClick={() => setVersionOpen(true)}>
              <PencilIcon />
              New version
            </Button>
          )
        }
      />
      <Surface className="overflow-hidden">
        {testCases.isPending ? (
          <TableSkeleton rows={4} cols={1} />
        ) : testCases.isError ? (
          <ErrorState error={testCases.error} onRetry={() => void testCases.refetch()} />
        ) : testCases.data.length === 0 ? (
          <EmptyState
            icon={ClipboardListIcon}
            title="No test cases"
            description="Add a new version with at least one test case before running an evaluation against this dataset."
            action={
              isMember && (
                <Button onClick={() => setVersionOpen(true)}>
                  <PencilIcon />
                  New version
                </Button>
              )
            }
          />
        ) : (
          <ul className="divide-y divide-hairline">
            {testCases.data.map((tc) => (
              <li key={tc.id} className="px-5 py-3.5">
                <div className="flex items-start justify-between gap-3">
                  <p className="min-w-0 text-[13px] text-foreground">
                    {typeof tc.expected_behavior.description === "string" && tc.expected_behavior.description
                      ? tc.expected_behavior.description
                      : "No description"}
                  </p>
                  <div className="flex shrink-0 gap-1.5">
                    {tc.tags.map((tag) => (
                      <Chip key={tag} tone="neutral">
                        {tag}
                      </Chip>
                    ))}
                  </div>
                </div>
                <pre className="mt-1.5 overflow-x-auto rounded-lg bg-muted px-3 py-2 font-mono text-[11.5px] text-muted-foreground">
                  {JSON.stringify(tc.input)}
                </pre>
              </li>
            ))}
          </ul>
        )}
      </Surface>
      <CreateDatasetVersionDialog
        orgId={orgId}
        dataset={dataset.data}
        currentTestCases={testCases.data ?? []}
        open={versionOpen}
        onOpenChange={setVersionOpen}
      />
    </>
  );
}
