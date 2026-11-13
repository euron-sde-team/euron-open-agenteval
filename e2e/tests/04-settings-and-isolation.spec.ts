import { expect, test } from "@playwright/test";

import { RUN, asOwner, createIsolatedOwner, signIn, VIEWER } from "../helpers";

test("settings: inviting an account that does not exist yet fails cleanly, members list shows the real demo org", async ({
  page,
}) => {
  await asOwner(page, "/settings");
  await expect(page.getByRole("heading", { name: "Settings" })).toBeVisible();

  await expect(page.getByText(VIEWER.email)).toBeVisible();

  await page.getByRole("button", { name: /add member/i }).click();
  const dialog = page.getByRole("dialog");
  await dialog.locator("#invite-email").fill(`nobody-${RUN}@agenteval.demo`);
  await dialog.getByRole("button", { name: /^add member$/i }).click();
  // Self-hosted, no self-serve signup: inviting an account that was never created on
  // the server with `agenteval create-owner` is a real, honest failure, not a silent no-op.
  await expect(dialog.getByText(/not found|no account|does not exist/i)).toBeVisible();
});

test("settings: create an API key, see the plaintext once, then revoke it", async ({ page }) => {
  await asOwner(page, "/settings");
  await page.getByRole("tab", { name: /api keys/i }).click();

  await page.getByRole("button", { name: /new key/i }).click();
  const dialog = page.getByRole("dialog");
  const keyName = `e2e-key-${RUN}`;
  await dialog.locator("#key-name").fill(keyName);
  await dialog.getByRole("button", { name: /^create key$/i }).click();

  await expect(dialog.getByText(/shown once/i)).toBeVisible({ timeout: 60_000 });
  const plaintext = await dialog.locator("code").textContent();
  expect(plaintext).toMatch(/^aek_/);
  await dialog.getByRole("button", { name: /i have copied the key/i }).click();
  await expect(dialog).toBeHidden();

  const row = page.getByRole("row", { name: new RegExp(keyName) });
  await expect(row).toBeVisible();
  await row.getByRole("button", { name: /revoke/i }).click();
  await page.getByRole("button", { name: /^revoke$/i }).click();

  // A revoked key stays visible (dimmed), never silently disappears: the control plane's
  // own audit-trail convention, carried into this product too.
  await expect(row).toBeVisible();
});

test("tenant isolation: a member of one organization cannot see another organization's agents or datasets", async ({
  page,
  request,
}) => {
  // AgentEval is self-hosted with no public signup; a second, genuinely separate
  // organization is created under the same demo owner account via the real
  // POST /api/v1/orgs the dashboard's own org switcher uses (it only ever appears once
  // an account belongs to more than one organization, which this test now makes true).
  const { orgName } = await createIsolatedOwner(request, "owner@agenteval.demo", "dev-demo-password-not-for-production");

  await signIn(page);
  await page.getByRole("button", { name: /switch organization/i }).click();
  await page.getByRole("menuitem", { name: new RegExp(orgName) }).click();

  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
  await page.goto("/agents");
  await expect(page.getByText(/no agents registered/i)).toBeVisible();
  await page.goto("/datasets");
  await expect(page.getByText(/no datasets yet/i)).toBeVisible();
});
