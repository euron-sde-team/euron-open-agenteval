"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, unwrap } from "@/lib/api/client";
import type { EvaluationRunIn } from "@/lib/api/types";
import { isRunInProgress } from "@/lib/eval-status";
import { qk, STALE } from "@/lib/query-keys";

export function useRuns(orgId: string) {
  return useQuery({
    queryKey: qk.runs(orgId),
    queryFn: () => unwrap(api.GET("/api/v1/orgs/{org_id}/evaluation-runs", { params: { path: { org_id: orgId } } })),
    enabled: !!orgId,
    staleTime: STALE.list,
    // A run still in flight (pending_traces/queued/running) is polled faster so the
    // list's own status chips catch up without a manual refresh.
    refetchInterval: (query) => {
      const runs = query.state.data;
      return runs?.some((r) => isRunInProgress(r.status)) ? STALE.runInProgress : false;
    },
  });
}

export function useRun(orgId: string, runId: string | undefined) {
  return useQuery({
    queryKey: qk.run(orgId, runId ?? ""),
    queryFn: () =>
      unwrap(
        api.GET("/api/v1/orgs/{org_id}/evaluation-runs/{run_id}", {
          params: { path: { org_id: orgId, run_id: runId ?? "" } },
        }),
      ),
    enabled: !!orgId && !!runId,
    refetchInterval: (query) => (query.state.data && isRunInProgress(query.state.data.status) ? STALE.runInProgress : false),
  });
}

export function useQueueRun(orgId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: EvaluationRunIn) =>
      unwrap(api.POST("/api/v1/orgs/{org_id}/evaluation-runs", { params: { path: { org_id: orgId } }, body })),
    onSuccess: () => client.invalidateQueries({ queryKey: qk.runs(orgId) }),
  });
}

/** Makes a `recorded` adapter run claimable once the SDK has pushed every test case's
 * trace (it starts life as "pending_traces", never "queued", so the worker's claim
 * query never races the SDK still pushing traces). A no-op, safely re-callable, on any
 * other run. */
export function useActivateRun(orgId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (runId: string) =>
      unwrap(
        api.POST("/api/v1/orgs/{org_id}/evaluation-runs/{run_id}/activate", {
          params: { path: { org_id: orgId, run_id: runId } },
        }),
      ),
    onSuccess: (_data, runId) => {
      void client.invalidateQueries({ queryKey: qk.runs(orgId) });
      void client.invalidateQueries({ queryKey: qk.run(orgId, runId) });
    },
  });
}

export function useJudgeCall(orgId: string, resultId: string | undefined, enabled: boolean) {
  return useQuery({
    queryKey: qk.judgeCall(orgId, resultId ?? ""),
    queryFn: () =>
      unwrap(
        api.GET("/api/v1/orgs/{org_id}/evaluation-results/{result_id}/judge-call", {
          params: { path: { org_id: orgId, result_id: resultId ?? "" } },
        }),
      ),
    enabled: !!orgId && !!resultId && enabled,
  });
}
