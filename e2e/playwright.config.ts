import { defineConfig, devices } from "@playwright/test";

/**
 * Browser end-to-end tests against the running local stack (`make up && make demo`): the
 * dashboard, the API, worker, Postgres and Redis.
 *
 *   pnpm test                 every suite
 *   E2E_HEADED=1 pnpm test    watch it
 *
 * The suites share one demo database, so they run in a single worker, in file order, and
 * each run's own fixtures (agents, datasets, organizations) are suffixed with a fresh RUN
 * id so two runs in a row never collide on name. They are NOT safe to repeat
 * indefinitely against the same seed, though: 03-results-and-traces exercises the demo
 * seed's own two completed runs by id, and a run's results are append-only once scored,
 * so re-running against the same seed is fine there; but any spec that queues a NEW run
 * against the shared default organization's agents/datasets grows that organization's
 * history every time, which is by design (benchmarks need history), not a problem, run
 * `make down && make up && make demo` for a genuinely fresh baseline if you want the
 * Benchmarks trend chart to show exactly the two seeded runs again.
 */
export default defineConfig({
  testDir: "./tests",
  globalSetup: "./global-setup.ts",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  // This machine routinely runs several other sessions' full Compose stacks
  // concurrently; a single real request has taken over 45s under that contention
  // during this suite's own development, not from anything wrong in the app or the
  // test, so both timeouts are generous rather than tuned to a quiet machine's numbers.
  timeout: 120_000,
  expect: { timeout: 30_000 },
  reporter: [["list"], ["html", { outputFolder: "playwright-report", open: "never" }]],
  outputDir: "test-results",
  use: {
    baseURL: process.env.WEB_URL || "http://localhost:5710",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    headless: !process.env.E2E_HEADED,
    storageState: ".auth/owner.json",
    viewport: { width: 1440, height: 900 },
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } } }],
});
