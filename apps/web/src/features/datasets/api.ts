"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, unwrap } from "@/lib/api/client";
import type { DatasetCreate, DatasetVersionUpdate } from "@/lib/api/types";
import { qk, STALE } from "@/lib/query-keys";

export function useDatasets(orgId: string) {
  return useQuery({
    queryKey: qk.datasets(orgId),
    queryFn: () => unwrap(api.GET("/api/v1/orgs/{org_id}/datasets", { params: { path: { org_id: orgId } } })),
    enabled: !!orgId,
    staleTime: STALE.list,
  });
}

export function useDataset(orgId: string, datasetId: string | undefined) {
  return useQuery({
    queryKey: qk.dataset(orgId, datasetId ?? ""),
    queryFn: () =>
      unwrap(
        api.GET("/api/v1/orgs/{org_id}/datasets/{dataset_id}", {
          params: { path: { org_id: orgId, dataset_id: datasetId ?? "" } },
        }),
      ),
    enabled: !!orgId && !!datasetId,
  });
}

export function useCreateDataset(orgId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: DatasetCreate) =>
      unwrap(api.POST("/api/v1/orgs/{org_id}/datasets", { params: { path: { org_id: orgId } }, body })),
    onSuccess: () => client.invalidateQueries({ queryKey: qk.datasets(orgId) }),
  });
}

export function useTestCases(orgId: string, datasetId: string | undefined) {
  return useQuery({
    queryKey: qk.testCases(orgId, datasetId ?? ""),
    queryFn: () =>
      unwrap(
        api.GET("/api/v1/orgs/{org_id}/datasets/{dataset_id}/test-cases", {
          params: { path: { org_id: orgId, dataset_id: datasetId ?? "" } },
        }),
      ),
    enabled: !!orgId && !!datasetId,
  });
}

export function useTestCasesForVersion(orgId: string, datasetVersionId: string | undefined) {
  return useQuery({
    queryKey: qk.testCasesForVersion(orgId, datasetVersionId ?? ""),
    queryFn: () =>
      unwrap(
        api.GET("/api/v1/orgs/{org_id}/dataset-versions/{dataset_version_id}/test-cases", {
          params: { path: { org_id: orgId, dataset_version_id: datasetVersionId ?? "" } },
        }),
      ),
    enabled: !!orgId && !!datasetVersionId,
  });
}

/** Replacing a dataset's test cases creates a NEW version (AC10): past evaluation runs
 * keep their original dataset_version_id, so this can never change what a completed
 * run's score means. */
export function useCreateDatasetVersion(orgId: string, datasetId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: DatasetVersionUpdate) =>
      unwrap(
        api.POST("/api/v1/orgs/{org_id}/datasets/{dataset_id}/versions", {
          params: { path: { org_id: orgId, dataset_id: datasetId } },
          body,
        }),
      ),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: qk.dataset(orgId, datasetId) });
      void client.invalidateQueries({ queryKey: qk.testCases(orgId, datasetId) });
      void client.invalidateQueries({ queryKey: qk.datasets(orgId) });
    },
  });
}
