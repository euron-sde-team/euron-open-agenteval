"use client";

import { useQuery } from "@tanstack/react-query";

import { api, unwrap } from "@/lib/api/client";
import { qk } from "@/lib/query-keys";

export function useBenchmarkCompare(
  orgId: string,
  baselineRunId: string | undefined,
  candidateRunId: string | undefined,
) {
  return useQuery({
    queryKey: qk.benchmarkCompare(orgId, baselineRunId ?? "", candidateRunId ?? ""),
    queryFn: () =>
      unwrap(
        api.GET("/api/v1/orgs/{org_id}/benchmarks/compare", {
          params: {
            path: { org_id: orgId },
            query: { baseline_run_id: baselineRunId ?? "", candidate_run_id: candidateRunId ?? "" },
          },
        }),
      ),
    enabled: !!orgId && !!baselineRunId && !!candidateRunId && baselineRunId !== candidateRunId,
  });
}

export function useBenchmarkTrend(orgId: string, runIds: string[]) {
  return useQuery({
    queryKey: qk.benchmarkTrend(orgId, runIds),
    queryFn: () =>
      unwrap(
        api.GET("/api/v1/orgs/{org_id}/benchmarks/trend", {
          params: { path: { org_id: orgId }, query: { run_ids: runIds } },
        }),
      ),
    enabled: !!orgId && runIds.length > 1,
  });
}
