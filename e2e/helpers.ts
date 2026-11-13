import { type APIRequestContext, expect, type Page } from "@playwright/test";

export const OWNER = {
  email: process.env.E2E_EMAIL || "owner@agenteval.demo",
  password: process.env.E2E_PASSWORD || process.env.AE_DEMO_PASSWORD || "dev-demo-password-not-for-production",
};

export const MEMBER = {
  email: "priya@agenteval.demo",
  password: OWNER.password,
};

export const VIEWER = {
  email: "sam@agenteval.demo",
  password: OWNER.password,
};

/** The demo seed's own organization (see apps/api/src/agenteval/demo/seed.py). The
 * dashboard falls back to organizations[0], sorted by name, whenever no active
 * organization is set in this browser's localStorage; since 04's own tenant-isolation
 * test creates new "Isolated Org <run>" organizations under this SAME demo owner
 * account, and "I" sorts before "N", a fresh browser context (every test gets one from
 * storageState) can silently land on a leftover isolated org from an earlier run
 * instead of the real demo org. Every spec that depends on the demo org's own seeded
 * data switches to it explicitly rather than trusting that fallback order. */
export const DEMO_ORG_NAME = "Northwind Labs";

/** A per-run suffix so suites can run repeatedly against the same demo database. */
export const RUN = process.env.E2E_RUN || Date.now().toString(36).slice(-5);

/** Open the dashboard with the shared owner session from global setup, on the real
 * demo organization regardless of how many other organizations this account has
 * accumulated from earlier runs of 04's tenant-isolation test. */
export async function asOwner(page: Page, path = "/"): Promise<void> {
  await page.goto("/");
  await expect(page.getByRole("button", { name: "Account menu" })).toBeVisible();
  const switcher = page.getByRole("button", { name: /switch organization/i });
  if (await switcher.isVisible().catch(() => false)) {
    const alreadyActive = await page
      .locator('[aria-label="Switch organization"]')
      .getByText(DEMO_ORG_NAME, { exact: true })
      .isVisible()
      .catch(() => false);
    if (!alreadyActive) {
      await switcher.click();
      await page.getByRole("menuitem", { name: DEMO_ORG_NAME, exact: true }).click();
    }
  }
  if (path !== "/") await page.goto(path);
}

/** Sign in through the real form (for auth tests and other users). */
export async function signIn(page: Page, email = OWNER.email, password = OWNER.password): Promise<void> {
  await page.goto("/login");
  await page.locator("#email").fill(email);
  await page.locator("#password").fill(password);
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
}

/** Pick an option in one of the dashboard's custom selects (@base-ui/react) that has
 * an id on its trigger. */
export async function choose(page: Page, triggerId: string, option: string | RegExp): Promise<void> {
  await page.locator(`#${triggerId}`).click();
  await page.getByRole("option", { name: option }).first().click();
}

/** Pick an option in a combobox with no id, located by its visible placeholder text
 * (the Benchmarks screen's baseline/candidate run selects have no id). */
export async function chooseByPlaceholder(page: Page, placeholder: string, option: string | RegExp): Promise<void> {
  await page.getByRole("combobox").filter({ hasText: placeholder }).click();
  await page.getByRole("option", { name: option }).first().click();
}

/** Create a brand new user (lands in "Default organization" as its owner) through the
 * real create-owner path exposed over HTTP: there is no self-serve signup, so a second,
 * isolated tenant for UI-level isolation checks is created by signing in as that fresh
 * owner and letting them create their own second organization through the real
 * POST /api/v1/orgs the dashboard's own "create organization" prompt uses. */
export async function createIsolatedOwner(
  request: APIRequestContext,
  email: string,
  password: string,
): Promise<{ orgId: string; orgName: string }> {
  const login = await request.post("/api/v1/auth/login", { data: { email, password } });
  if (!login.ok()) {
    throw new Error(`could not sign in as ${email} (${login.status()}): seed it with agenteval create-owner first`);
  }
  const orgName = `Isolated Org ${RUN}`;
  // A cookie-authenticated mutation needs the real CSRF header (see
  // auth/dependencies.py): browsers never attach a custom header cross-site, so this is
  // the server's actual CSRF defense, not an incidental requirement to work around.
  const created = await request.post("/api/v1/orgs", {
    data: { name: orgName },
    headers: { "x-agenteval-csrf": "1" },
  });
  if (!created.ok()) throw new Error(`could not create a second organization (${created.status()})`);
  const org = await created.json();
  return { orgId: org.id as string, orgName };
}
