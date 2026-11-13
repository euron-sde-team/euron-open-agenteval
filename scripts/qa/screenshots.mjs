/**
 * Curated README screenshots from a freshly seeded stack.
 *
 *   make up && make demo
 *   cd scripts/qa && QA_BASE=http://localhost:5710 node screenshots.mjs
 *
 * Writes docs/assets/screenshots/NN-name.png. Signs in as the demo owner and switches
 * to the demo seed's own organization explicitly (see DEMO_ORG_NAME in qa.mjs), the same
 * fix qa.mjs needed: this account can accumulate other organizations over time (e.g. from
 * the e2e suite's tenant-isolation test), so the dashboard's own organizations[0]
 * fallback is not reliably the real demo org.
 */
import { mkdir } from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import puppeteer from "puppeteer";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const BASE = process.env.QA_BASE ?? "http://localhost:5710";
const EMAIL = process.env.QA_EMAIL ?? "owner@agenteval.demo";
const PASSWORD = process.env.QA_PASSWORD ?? process.env.AE_DEMO_PASSWORD ?? "dev-demo-password-not-for-production";
const DEMO_ORG_NAME = process.env.QA_ORG ?? "Northwind Labs";
const SHOTS = path.resolve(HERE, "../../docs/assets/screenshots");
const CHROME = process.env.CHROME_PATH && existsSync(process.env.CHROME_PATH) ? process.env.CHROME_PATH : undefined;
const DESKTOP = { width: 1440, height: 900, deviceScaleFactor: 1 };
const PHONE = { width: 390, height: 844, deviceScaleFactor: 2, isMobile: true, hasTouch: true };

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function settle(page, ms = 1800) {
  await page.waitForNetworkIdle({ idleTime: 400, timeout: 30_000 }).catch(() => {});
  await page
    .waitForSelector('[data-slot="skeleton"], .animate-pulse', { hidden: true, timeout: 15_000 })
    .catch(() => {});
  await sleep(ms);
}

async function shot(page, name, { fullPage = false } = {}) {
  await page.screenshot({ path: path.join(SHOTS, `${name}.png`), fullPage });
  console.log(`saved ${name}`);
}

async function setActiveOrg(page, orgId) {
  await page.evaluate((id) => {
    const raw = localStorage.getItem("agenteval.ui");
    const parsed = raw ? JSON.parse(raw) : { state: {}, version: 1 };
    parsed.state = { ...parsed.state, activeOrgId: id };
    localStorage.setItem("agenteval.ui", JSON.stringify(parsed));
  }, orgId);
}

async function main() {
  await mkdir(SHOTS, { recursive: true });
  const browser = await puppeteer.launch({ executablePath: CHROME, headless: true, args: ["--no-sandbox"] });
  const ctx = await browser.createBrowserContext();
  const page = await ctx.newPage();
  await page.setViewport(DESKTOP);
  await page.evaluateOnNewDocument(() => {
    try {
      localStorage.setItem("theme", "light");
    } catch {}
  });

  await page.goto(`${BASE}/login`, { waitUntil: "networkidle2", timeout: 60_000 });
  await sleep(600);
  await shot(page, "00-sign-in");
  await page.type("#email", EMAIL);
  await page.type("#password", PASSWORD);
  await Promise.all([
    page.waitForNavigation({ waitUntil: "networkidle2", timeout: 60_000 }),
    page.click("button[type=submit]"),
  ]);

  const demoOrgId = await page.evaluate(async (name) => {
    const orgs = await (await fetch("/api/v1/orgs")).json();
    return orgs.find((o) => o.name === name)?.id ?? null;
  }, DEMO_ORG_NAME);
  if (!demoOrgId) throw new Error(`organization "${DEMO_ORG_NAME}" not found: run make demo first`);
  await setActiveOrg(page, demoOrgId);

  await page.goto(`${BASE}/`, { waitUntil: "networkidle2", timeout: 60_000 });
  await settle(page);
  await shot(page, "01-overview");

  await page.goto(`${BASE}/agents`, { waitUntil: "networkidle2", timeout: 60_000 });
  await settle(page);
  await shot(page, "02-agents");

  await page.goto(`${BASE}/datasets`, { waitUntil: "networkidle2", timeout: 60_000 });
  await settle(page);
  await shot(page, "03-datasets");

  await page.goto(`${BASE}/evaluations`, { waitUntil: "networkidle2", timeout: 60_000 });
  await settle(page);
  await shot(page, "04-evaluations");

  // A completed run's result breakdown, expanded to show the deterministic/judge split.
  await page.waitForSelector("table tbody tr a");
  const href = await page.$eval("table tbody tr a", (a) => a.getAttribute("href"));
  await page.goto(`${BASE}${href}`, { waitUntil: "networkidle2", timeout: 60_000 });
  await settle(page);
  await shot(page, "05-run-detail", { fullPage: true });

  // That run's own execution trace, followed the real way: by id, not a browsable list.
  const traceId = await page.evaluate(async () => {
    const parts = location.pathname.split("/");
    const runId = parts[parts.length - 1];
    const orgRaw = localStorage.getItem("agenteval.ui");
    const orgId = JSON.parse(orgRaw).state.activeOrgId;
    const detail = await (await fetch(`/api/v1/orgs/${orgId}/evaluation-runs/${runId}`)).json();
    return detail.results.find((r) => r.trace_id)?.trace_id ?? null;
  });
  if (traceId) {
    await page.goto(`${BASE}/traces/${traceId}`, { waitUntil: "networkidle2", timeout: 60_000 });
    await settle(page);
    await shot(page, "06-execution-trace");
  }

  // Benchmarks: the real regression/improvement, baseline vs candidate populated.
  await page.goto(`${BASE}/benchmarks`, { waitUntil: "networkidle2", timeout: 60_000 });
  await settle(page);
  let combos = await page.$$('[role="combobox"]');
  await combos[0].click();
  await sleep(300);
  let options = await page.$$('[data-slot="select-content"][data-open] [role="option"]');
  await options[0].click();
  await sleep(600);
  combos = await page.$$('[role="combobox"]');
  await combos[1].click();
  await sleep(300);
  options = await page.$$('[data-slot="select-content"][data-open] [role="option"]');
  await options[1].click();
  await settle(page, 1500);
  await shot(page, "07-benchmarks");

  await page.goto(`${BASE}/reports`, { waitUntil: "networkidle2", timeout: 60_000 });
  await settle(page);
  await shot(page, "08-reports");

  await page.goto(`${BASE}/audit`, { waitUntil: "networkidle2", timeout: 60_000 });
  await settle(page);
  await shot(page, "09-audit-log");

  await page.goto(`${BASE}/settings`, { waitUntil: "networkidle2", timeout: 60_000 });
  await settle(page);
  await shot(page, "10-settings");

  // Dark mode: next-themes reads localStorage only from its inline script at initial
  // load, so the value must be set before a fresh navigation, not written into an
  // already-loaded page (confirmed: that produced a screenshot still in light mode).
  await page.evaluateOnNewDocument(() => {
    try {
      localStorage.setItem("theme", "dark");
    } catch {}
  });
  await page.goto(`${BASE}/`, { waitUntil: "networkidle2", timeout: 60_000 });
  await settle(page);
  await shot(page, "11-dark-mode");

  // Phone width, light mode.
  const phone = await ctx.newPage();
  await phone.setViewport(PHONE);
  await phone.evaluateOnNewDocument(() => {
    try {
      localStorage.setItem("theme", "light");
    } catch {}
  });
  await phone.goto(`${BASE}/`, { waitUntil: "networkidle2", timeout: 60_000 });
  await settle(phone);
  await phone.screenshot({ path: path.join(SHOTS, "12-mobile.png") });
  console.log("saved 12-mobile");

  await browser.close();
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
