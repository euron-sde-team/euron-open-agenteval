import { describe, expect, it } from "vitest";

import {
  adapterTypeLabel,
  deltaTone,
  formatDelta,
  isRunInProgress,
  methodLabel,
  resultTone,
  runStatusLabel,
  runStatusTone,
  scorePercent,
} from "@/lib/eval-status";

describe("runStatusLabel", () => {
  it("maps every real run status to a human label", () => {
    expect(runStatusLabel("pending_traces")).toBe("Waiting for traces");
    expect(runStatusLabel("queued")).toBe("Queued");
    expect(runStatusLabel("running")).toBe("Running");
    expect(runStatusLabel("completed")).toBe("Completed");
    expect(runStatusLabel("failed")).toBe("Failed");
  });

  it("falls back to the raw value for an unrecognized status", () => {
    expect(runStatusLabel("something_else")).toBe("something_else");
  });
});

describe("runStatusTone", () => {
  it("maps completed to savings and failed to danger", () => {
    expect(runStatusTone("completed")).toBe("savings");
    expect(runStatusTone("failed")).toBe("danger");
  });

  it("maps running to primary and the two queue states to warning", () => {
    expect(runStatusTone("running")).toBe("primary");
    expect(runStatusTone("queued")).toBe("warning");
    expect(runStatusTone("pending_traces")).toBe("warning");
  });

  it("falls back to neutral for an unrecognized status", () => {
    expect(runStatusTone("something_else")).toBe("neutral");
  });
});

describe("isRunInProgress", () => {
  it("is true for pending_traces, queued, and running", () => {
    expect(isRunInProgress("pending_traces")).toBe(true);
    expect(isRunInProgress("queued")).toBe(true);
    expect(isRunInProgress("running")).toBe(true);
  });

  it("is false for completed and failed", () => {
    expect(isRunInProgress("completed")).toBe(false);
    expect(isRunInProgress("failed")).toBe(false);
  });
});

describe("methodLabel", () => {
  it("labels judge as judge scored and anything else as deterministic", () => {
    expect(methodLabel("judge")).toBe("Judge scored");
    expect(methodLabel("exact_match")).toBe("Deterministic");
  });
});

describe("resultTone", () => {
  it("maps passed to savings and failed to danger", () => {
    expect(resultTone(true)).toBe("savings");
    expect(resultTone(false)).toBe("danger");
  });
});

describe("scorePercent", () => {
  it("rounds a 0 to 1 score to a whole percent", () => {
    expect(scorePercent(0.873)).toBe("87%");
    expect(scorePercent(1)).toBe("100%");
    expect(scorePercent(0)).toBe("0%");
  });
});

describe("deltaTone", () => {
  it("is danger whenever is_regression is true, regardless of delta sign", () => {
    expect(deltaTone(0.1, true)).toBe("danger");
    expect(deltaTone(-0.1, true)).toBe("danger");
  });

  it("is savings for a positive delta that is not a regression", () => {
    expect(deltaTone(0.1, false)).toBe("savings");
  });

  it("is neutral for a zero or negative delta that is not a regression", () => {
    expect(deltaTone(0, false)).toBe("neutral");
    expect(deltaTone(-0.1, false)).toBe("neutral");
  });
});

describe("formatDelta", () => {
  it("prefixes a positive delta with a plus sign", () => {
    expect(formatDelta(0.12)).toBe("+12%");
  });

  it("keeps the minus sign for a negative delta", () => {
    expect(formatDelta(-0.08)).toBe("-8%");
  });

  it("is a bare 0% for no change", () => {
    expect(formatDelta(0)).toBe("0%");
  });
});

describe("adapterTypeLabel", () => {
  it("maps every real adapter type to a human label", () => {
    expect(adapterTypeLabel("http")).toBe("HTTP endpoint");
    expect(adapterTypeLabel("python")).toBe("Python callable");
    expect(adapterTypeLabel("recorded")).toBe("Recorded traces");
  });

  it("falls back to the raw value for an unrecognized adapter type", () => {
    expect(adapterTypeLabel("something_else")).toBe("something_else");
  });
});
