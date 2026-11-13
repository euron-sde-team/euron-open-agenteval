/**
 * Pure mappings from the API's real status/score/method values to what the dashboard
 * shows. Mirrors the server's own vocabulary exactly (agenteval.evaluations.models'
 * run statuses, agenteval.evaluators.schema's metric methods): never a value invented
 * on the client that the server does not also use.
 */

export type RunStatus = "pending_traces" | "queued" | "running" | "completed" | "failed";

export function runStatusLabel(status: string): string {
  switch (status as RunStatus) {
    case "pending_traces":
      return "Waiting for traces";
    case "queued":
      return "Queued";
    case "running":
      return "Running";
    case "completed":
      return "Completed";
    case "failed":
      return "Failed";
    default:
      return status;
  }
}

export function runStatusTone(status: string): "primary" | "warning" | "danger" | "savings" | "neutral" {
  switch (status as RunStatus) {
    case "completed":
      return "savings";
    case "failed":
      return "danger";
    case "running":
      return "primary";
    case "pending_traces":
    case "queued":
      return "warning";
    default:
      return "neutral";
  }
}

export function isRunInProgress(status: string): boolean {
  return status === "pending_traces" || status === "queued" || status === "running";
}

export function methodLabel(method: string): string {
  return method === "judge" ? "Judge scored" : "Deterministic";
}

/** A metric's own pass/fail color, never the run's overall status color. */
export function resultTone(passed: boolean): "savings" | "danger" {
  return passed ? "savings" : "danger";
}

export function scorePercent(score: number): string {
  return `${Math.round(score * 100)}%`;
}

export function deltaTone(delta: number, isRegression: boolean): "savings" | "danger" | "neutral" {
  if (isRegression) return "danger";
  if (delta > 0) return "savings";
  return "neutral";
}

export function formatDelta(delta: number): string {
  const pct = Math.round(delta * 100);
  if (pct === 0) return "0%";
  return pct > 0 ? `+${pct}%` : `${pct}%`;
}

export function adapterTypeLabel(adapterType: string): string {
  switch (adapterType) {
    case "http":
      return "HTTP endpoint";
    case "python":
      return "Python callable";
    case "recorded":
      return "Recorded traces";
    default:
      return adapterType;
  }
}
