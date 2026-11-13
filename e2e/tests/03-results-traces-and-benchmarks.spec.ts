import { expect, test } from "@playwright/test";

import { asOwner, DEMO_ORG_NAME } from "../helpers";

/** The demo seed's own org has exactly the two seeded runs plus whatever this e2e suite
 * itself queues in file 02; find a specific seeded run by its known judge-scored
 * behaviour (task_success/accuracy/faithfulness/instruction_adherence) rather than
 * assuming table position, since the newest run is always first and 02 just added one.
 * Looks the demo org up by its real name, never organizations[0] (see helpers.ts's
 * DEMO_ORG_NAME docstring for why that index is not reliably the demo org). */
async function findJudgeScoredRun(page: import("@playwright/test").Page): Promise<string> {
  const orgId = await page.evaluate(async (name) => {
    const orgs = (await (await fetch("/api/v1/orgs")).json()) as Array<{ id: string; name: string }>;
    return orgs.find((o) => o.name === name)?.id as string;
  }, DEMO_ORG_NAME);
  const runs = await page.evaluate(
    async (id) => (await (await fetch(`/api/v1/orgs/${id}/evaluation-runs`)).json()) as Array<{
      id: string;
      status: string;
      metric_ids: string[];
    }>,
    orgId,
  );
  const judgeMetrics = ["task_success", "accuracy", "faithfulness", "instruction_adherence"];
  const found = runs.find((r) => r.status === "completed" && r.metric_ids.some((m) => judgeMetrics.includes(m)));
  if (!found) throw new Error("expected at least one completed, judge-scored run from the demo seed");
  return found.id;
}

test("a completed run's result expands to show its method, reveals the judge call, and links to its trace", async ({
  page,
}) => {
  await asOwner(page, "/evaluations");
  await expect(page.getByRole("heading", { name: "Evaluations" })).toBeVisible();

  const runId = await findJudgeScoredRun(page);
  await page.goto(`/evaluations/${runId}`);
  await expect(page.getByRole("heading", { name: /^run [0-9a-f]{8}$/i })).toBeVisible();

  const rows = await page.locator("li").filter({ has: page.getByText(/^(passed|failed)$/i) }).all();
  expect(rows.length).toBeGreaterThan(0);

  let revealed = false;
  let tracedResultIndex = -1;
  for (let i = 0; i < rows.length; i++) {
    await rows[i].locator("button").first().click();
    const revealButton = rows[i].getByRole("button", { name: /reveal judge prompt and response/i });
    if (await revealButton.isVisible().catch(() => false)) {
      await revealButton.click();
      await expect(rows[i].getByText("Prompt sent to the judge")).toBeVisible();
      await expect(rows[i].getByText("Raw judge response")).toBeVisible();
      revealed = true;
    }
    const traceLink = rows[i].getByRole("link", { name: /view the execution trace/i });
    if (tracedResultIndex === -1 && (await traceLink.isVisible().catch(() => false))) {
      tracedResultIndex = i;
    }
    if (revealed && tracedResultIndex !== -1) break;
  }
  expect(revealed, "expected at least one judge-scored result to reveal").toBe(true);
  expect(tracedResultIndex, "expected at least one result linked to a trace").toBeGreaterThanOrEqual(0);

  await rows[tracedResultIndex].getByRole("link", { name: /view the execution trace/i }).click();
  await expect(page).toHaveURL(/\/traces\/[0-9a-f-]+/);
  await expect(page.getByRole("heading", { name: /^trace /i })).toBeVisible();
});

test("benchmarks: pairwise comparison shows the real exact_match regression, trend across the seeded runs renders", async ({
  page,
}) => {
  await asOwner(page, "/benchmarks");
  await expect(page.getByRole("heading", { name: "Benchmarks" })).toBeVisible();

  const runLabels = page.locator("label").filter({ hasText: /^[0-9a-f]{8}$/ });
  const count = await runLabels.count();
  expect(count).toBeGreaterThanOrEqual(2);

  // Baseline/candidate selects have no id: locate by the real placeholder text, and
  // scope option clicks to the currently open popup (base-ui keeps a closing popup's
  // options briefly present during its exit animation, which made an unscoped
  // getByRole("option") locator flake against the wrong, closing popup).
  await page.getByRole("combobox").filter({ hasText: /baseline run/i }).click();
  await page.locator('[data-slot="select-content"][data-open]').getByRole("option").first().click();
  await page.getByRole("combobox").filter({ hasText: /candidate run/i }).click();
  await page.locator('[data-slot="select-content"][data-open]').getByRole("option").nth(1).click();

  await expect(page.getByRole("cell", { name: "exact_match" })).toBeVisible({ timeout: 20_000 });

  // AC9: pick every seeded run for the trend chart.
  for (let i = 0; i < count; i++) {
    await runLabels.nth(i).click();
  }
  await expect(page.getByText(/pick at least two runs/i)).toBeHidden();
});
