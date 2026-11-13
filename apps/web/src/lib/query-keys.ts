/**
 * Query keys in one place, so invalidation after a mutation names exactly what it
 * touched. Every list is scoped under the signed-in organization's id.
 */
export const qk = {
  me: ["auth", "me"] as const,
  orgs: ["orgs"] as const,
  members: (orgId: string) => ["orgs", orgId, "members"] as const,
  apiKeys: (orgId: string) => ["orgs", orgId, "api-keys"] as const,
  auditLog: (orgId: string) => ["orgs", orgId, "audit-log"] as const,
  agents: (orgId: string) => ["orgs", orgId, "agents"] as const,
  agentVersions: (orgId: string, agentId: string) => ["orgs", orgId, "agents", agentId, "versions"] as const,
  datasets: (orgId: string) => ["orgs", orgId, "datasets"] as const,
  dataset: (orgId: string, datasetId: string) => ["orgs", orgId, "datasets", "detail", datasetId] as const,
  testCases: (orgId: string, datasetId: string) =>
    ["orgs", orgId, "datasets", datasetId, "test-cases"] as const,
  testCasesForVersion: (orgId: string, datasetVersionId: string) =>
    ["orgs", orgId, "dataset-versions", datasetVersionId, "test-cases"] as const,
  runs: (orgId: string) => ["orgs", orgId, "evaluation-runs"] as const,
  run: (orgId: string, runId: string) => ["orgs", orgId, "evaluation-runs", "detail", runId] as const,
  judgeCall: (orgId: string, resultId: string) =>
    ["orgs", orgId, "evaluation-results", resultId, "judge-call"] as const,
  trace: (orgId: string, traceId: string) => ["orgs", orgId, "traces", "detail", traceId] as const,
  traceForRunAndCase: (orgId: string, runId: string, testCaseId: string) =>
    ["orgs", orgId, "evaluation-runs", runId, "test-cases", testCaseId, "trace"] as const,
  benchmarkCompare: (orgId: string, baselineRunId: string, candidateRunId: string) =>
    ["orgs", orgId, "benchmarks", "compare", baselineRunId, candidateRunId] as const,
  benchmarkTrend: (orgId: string, runIds: string[]) =>
    ["orgs", orgId, "benchmarks", "trend", ...runIds] as const,
};

/** staleTime per kind of data, chosen deliberately. A running evaluation polls faster. */
export const STALE = {
  config: 30_000,
  list: 10_000,
  runInProgress: 2_000,
} as const;
