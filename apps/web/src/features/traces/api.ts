"use client";

import { useQuery } from "@tanstack/react-query";

import { api, unwrap } from "@/lib/api/client";
import { qk } from "@/lib/query-keys";

export function useTrace(orgId: string, traceId: string | undefined) {
  return useQuery({
    queryKey: qk.trace(orgId, traceId ?? ""),
    queryFn: () =>
      unwrap(
        api.GET("/api/v1/orgs/{org_id}/traces/{trace_id}", {
          params: { path: { org_id: orgId, trace_id: traceId ?? "" } },
        }),
      ),
    enabled: !!orgId && !!traceId,
  });
}

/** AC6: the same trace is reachable from the run/result side (not just by trace id),
 * so opening a scored result always offers its matching execution trace. */
export function useTraceForRunAndCase(orgId: string, runId: string | undefined, testCaseId: string | undefined) {
  return useQuery({
    queryKey: qk.traceForRunAndCase(orgId, runId ?? "", testCaseId ?? ""),
    queryFn: () =>
      unwrap(
        api.GET("/api/v1/orgs/{org_id}/evaluation-runs/{run_id}/test-cases/{test_case_id}/trace", {
          params: { path: { org_id: orgId, run_id: runId ?? "", test_case_id: testCaseId ?? "" } },
        }),
      ),
    enabled: !!orgId && !!runId && !!testCaseId,
    retry: false,
  });
}
