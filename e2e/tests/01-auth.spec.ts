import { expect, test } from "@playwright/test";

import { OWNER, signIn } from "../helpers";

// These tests exercise the sign-in form itself, so they start signed out.
test.use({ storageState: { cookies: [], origins: [] } });

test("wrong password shows an actionable error", async ({ page }) => {
  await page.goto("/login");
  await page.locator("#email").fill(OWNER.email);
  await page.locator("#password").fill("definitely-wrong-9");
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page.getByText(/email or password is incorrect/i)).toBeVisible();
});

test("signed-out visitors are sent to sign in", async ({ page }) => {
  await page.goto("/agents");
  await expect(page).toHaveURL(/\/login/);
});

test("owner signs in, sees the overview, and signs out", async ({ page }) => {
  await signIn(page);
  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
  await page.getByRole("button", { name: "Account menu" }).click();
  await page.getByText("Sign out", { exact: true }).click();
  await expect(page).toHaveURL(/\/login/);
});
