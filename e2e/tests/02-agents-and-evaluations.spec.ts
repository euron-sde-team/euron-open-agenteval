import { expect, test } from "@playwright/test";

import { RUN, asOwner, choose } from "../helpers";

test("register an agent, add a version, create a dataset, and run an evaluation to completion", async ({ page }) => {
  await asOwner(page, "/agents");
  await expect(page.getByRole("heading", { name: "Agents" })).toBeVisible();

  // Register the agent (python adapter, pointed at the real toy agent shipped for exactly
  // this: no real framework or API key needed to run a live evaluation end to end).
  await page.getByRole("button", { name: /register agent/i }).click();
  const registerDialog = page.getByRole("dialog");
  await registerDialog.locator("#agent-name").fill(`e2e-agent-${RUN}`);
  await choose(page, "agent-adapter", "Python callable");
  await registerDialog.getByRole("button", { name: /^register$/i }).click();
  await expect(registerDialog).toBeHidden({ timeout: 30_000 });

  const agentRow = page.getByRole("row", { name: new RegExp(`e2e-agent-${RUN}`) });
  await expect(agentRow).toBeVisible();
  await agentRow.getByRole("link", { name: new RegExp(`e2e-agent-${RUN}`) }).click();
  await expect(page.getByRole("heading", { name: `e2e-agent-${RUN}` })).toBeVisible();

  // Add a version pointing at the real toy_agent module.
  await page.getByRole("button", { name: /new version/i }).click();
  const versionDialog = page.getByRole("dialog");
  await versionDialog.locator("#version-label").fill(`v1-${RUN}`);
  await versionDialog.locator("#version-config").fill("agenteval.examples.toy_agent:answer");
  await versionDialog.getByRole("button", { name: /^create version$/i }).click();
  await expect(versionDialog).toBeHidden({ timeout: 30_000 });
  await expect(page.getByText(`v1-${RUN}`).first()).toBeVisible();

  // Create a dataset with one deterministic and one tool-calling test case, both of
  // which the real toy agent answers correctly.
  await page.goto("/datasets");
  await page.getByRole("button", { name: /create dataset/i }).click();
  const datasetDialog = page.getByRole("dialog");
  await datasetDialog.locator("#dataset-name").fill(`e2e-dataset-${RUN}`);
  await datasetDialog.locator("#dataset-cases").fill(
    JSON.stringify([
      {
        input: { question: "What is the capital of France?" },
        expected_behavior: {
          description: "State the capital of France correctly.",
          exact_match: "The capital of France is Paris.",
        },
        tags: ["geography"],
      },
      {
        input: { question: "What is 2 + 2?" },
        expected_behavior: {
          description: "Use the calculator tool to answer the arithmetic question.",
          required_tool_calls: ["calculator"],
        },
        tags: ["arithmetic"],
      },
    ]),
  );
  await datasetDialog.getByRole("button", { name: /^create$/i }).click();
  await expect(datasetDialog).toBeHidden({ timeout: 30_000 });
  await expect(page.getByText(`e2e-dataset-${RUN}`).first()).toBeVisible();

  // Queue a run against the new agent version and dataset, deterministic checks only
  // (no judge call needed, proving AC3's zero-judge-call path through the real UI).
  await page.goto("/evaluations");
  await page.getByRole("button", { name: /queue run/i }).click();
  const runDialog = page.getByRole("dialog");
  await choose(page, "run-agent", new RegExp(`e2e-agent-${RUN}`));
  await choose(page, "run-agent-version", new RegExp(`v1-${RUN}`));
  await choose(page, "run-dataset", new RegExp(`e2e-dataset-${RUN}`));
  await runDialog.getByRole("button", { name: /^queue run$/i }).click();
  await expect(runDialog).toBeHidden({ timeout: 30_000 });

  // Poll until the worker (a real background process against the real Postgres queue,
  // FOR UPDATE SKIP LOCKED) claims and completes the run.
  const firstRunRow = page.locator("table tbody tr").first();
  await expect(firstRunRow.getByText(/completed/i)).toBeVisible({ timeout: 30_000 });

  await firstRunRow.locator("a").first().click();
  await expect(page.getByRole("heading", { name: /^run [0-9a-f]{8}$/i })).toBeVisible();
  // Both results present and passed: the deterministic exact-match and the
  // tool-calling check, scored from the toy agent's real output, not a stub.
  await expect(page.getByText("exact_match")).toBeVisible();
  await expect(page.getByText("required_tool_called")).toBeVisible();
  await expect(page.getByText("Passed").first()).toBeVisible();
});
