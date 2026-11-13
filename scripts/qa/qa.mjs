/**
 * Browser QA (make qa): signs in through the real form, visits every dashboard page in
 * light and dark at desktop and phone width, saves screenshots, and fails on console
 * errors, failed or 4xx/5xx requests, broken images, error states and horizontal overflow.
 *
 *   make qa
 *   QA_BASE=http://localhost:5710 QA_OUT=./output node qa.mjs
 *   QA_PAGES=/,/agents QA_THEMES=dark QA_SIZES=desktop node qa.mjs
 *
 * Uses Puppeteer's bundled Chromium; set CHROME_PATH to use a local browser instead.
 *
 * /traces has no list-all screen (lookup by id only, see traces-screen.tsx), so it is
 * reached through a real run's result instead of crawled directly; this script resolves
 * one trace id from the demo seed's own completed runs the same way, before the sweep.
 *
 * Every page is visited as the demo seed's own organization (see DEMO_ORG_NAME below),
 * switched to explicitly right after sign-in rather than trusted to whatever the
 * dashboard's own organizations[0] fallback picks for this account.
 */
import { mkdir } from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";
import puppeteer from "puppeteer";

const BASE = process.env.QA_BASE ?? "http://localhost:5710";
const OUT = process.env.QA_OUT ?? path.resolve("output");
const EMAIL = process.env.QA_EMAIL ?? "owner@agenteval.demo";
const PASSWORD = process.env.QA_PASSWORD ?? process.env.AE_DEMO_PASSWORD ?? "dev-demo-password-not-for-production";
const CHROME = process.env.CHROME_PATH && existsSync(process.env.CHROME_PATH) ? process.env.CHROME_PATH : undefined;

/** The demo seed's own organization (apps/api/src/agenteval/demo/seed.py). The dashboard
 * falls back to organizations[0] whenever no active org is set in this browser's
 * localStorage, and this same demo owner account has since accumulated other
 * organizations (e.g. the e2e suite's own tenant-isolation test creates one every run),
 * so that fallback is not reliably this one. Every fresh browser context here switches
 * to it explicitly before the sweep instead of trusting the fallback order. */
const DEMO_ORG_NAME = process.env.QA_ORG ?? "Northwind Labs";

const STATIC_PAGES = [
  "/login",
  "/",
  "/agents",
  "/datasets",
  "/evaluations",
  "/benchmarks",
  "/reports",
  "/audit",
  "/settings",
];
const PAGES = process.env.QA_PAGES ? process.env.QA_PAGES.split(",") : [...STATIC_PAGES, "/traces/:firstTrace"];
const THEMES = (process.env.QA_THEMES ?? "light,dark").split(",");
const SIZES = {
  desktop: { width: 1440, height: 900 },
  phone: { width: 390, height: 844, isMobile: true, hasTouch: true, deviceScaleFactor: 2 },
};
const SIZE_KEYS = (process.env.QA_SIZES ?? "desktop,phone").split(",");
const FULL = process.env.QA_FULL !== "0";

function slug(p) {
  return p === "/" ? "overview" : p.replace(/^\//, "").replace(/[/:]/g, "-");
}

/** Set this browser context's persisted active org (zustand's "agenteval.ui" key), the
 * same source of truth every screen reads via useActiveOrg(). */
async function setActiveOrg(page, orgId) {
  await page.evaluate((id) => {
    const raw = localStorage.getItem("agenteval.ui");
    const parsed = raw ? JSON.parse(raw) : { state: {}, version: 1 };
    parsed.state = { ...parsed.state, activeOrgId: id };
    localStorage.setItem("agenteval.ui", JSON.stringify(parsed));
  }, orgId);
}

async function resolveDemoOrgId(page) {
  return page.evaluate(async (name) => {
    const orgs = await (await fetch("/api/v1/orgs")).json();
    return orgs.find((o) => o.name === name)?.id ?? null;
  }, DEMO_ORG_NAME);
}

/** The demo org's own first trace id, found through its completed runs' results. */
async function resolveFirstTrace(page, orgId) {
  return page.evaluate(async (id) => {
    const runs = await (await fetch(`/api/v1/orgs/${id}/evaluation-runs`)).json();
    for (const run of runs) {
      if (run.status !== "completed") continue;
      const detail = await (await fetch(`/api/v1/orgs/${id}/evaluation-runs/${run.id}`)).json();
      for (const result of detail.results ?? []) {
        if (result.trace_id) return result.trace_id;
      }
    }
    return null;
  }, orgId);
}

async function main() {
  await mkdir(OUT, { recursive: true });
  const browser = await puppeteer.launch({ executablePath: CHROME, headless: true, args: ["--no-sandbox"] });
  const problems = [];
  let firstTraceId = null;

  for (const theme of THEMES) {
    for (const sizeKey of SIZE_KEYS) {
      const ctx = await browser.createBrowserContext();
      const page = await ctx.newPage();
      await page.setViewport(SIZES[sizeKey]);
      await page.evaluateOnNewDocument((t) => {
        try {
          localStorage.setItem("theme", t);
        } catch {}
      }, theme);
      const consoleErrors = [];
      page.on("console", (m) => {
        if (m.type() === "error") consoleErrors.push(m.text());
      });
      page.on("pageerror", (e) => consoleErrors.push(`pageerror: ${e.message}`));
      page.on("requestfailed", (r) => {
        const err = r.failure()?.errorText ?? "";
        if (!err.includes("ERR_ABORTED")) consoleErrors.push(`requestfailed ${r.url()} ${err}`);
      });
      page.on("response", (r) => {
        if (r.status() >= 400) consoleErrors.push(`HTTP ${r.status()} ${r.url()}`);
      });

      // Sign in through the real form once per context.
      await page.goto(`${BASE}/login`, { waitUntil: "networkidle2", timeout: 60_000 });
      if (PAGES.includes("/login")) {
        await new Promise((r) => setTimeout(r, 400));
        await page.screenshot({ path: path.join(OUT, `${sizeKey}-${theme}-login.png`) });
      }
      await page.type("#email", EMAIL);
      await page.type("#password", PASSWORD);
      await Promise.all([
        page.waitForNavigation({ waitUntil: "networkidle2", timeout: 60_000 }),
        page.click("button[type=submit]"),
      ]);

      const demoOrgId = await resolveDemoOrgId(page);
      if (!demoOrgId) throw new Error(`organization "${DEMO_ORG_NAME}" not found: run make demo first`);
      await setActiveOrg(page, demoOrgId);
      if (!firstTraceId) {
        firstTraceId = await resolveFirstTrace(page, demoOrgId);
      }

      for (const p of PAGES) {
        if (p === "/login") continue;
        const url = p.replace(":firstTrace", firstTraceId ?? "missing");
        consoleErrors.length = 0;
        await page.goto(`${BASE}${url}`, { waitUntil: "networkidle2", timeout: 60_000 });
        // networkidle2 only requires <=2 in-flight requests, so a page with several
        // parallel queries (e.g. Overview's agents/datasets/runs stat cards) can still
        // have one genuinely in flight here, especially under this machine's real,
        // demonstrated contention from other sessions' stacks; give any last skeleton a
        // chance to resolve before judging and screenshotting the page.
        await page
          .waitForSelector('[data-slot="skeleton"], .animate-pulse', { hidden: true, timeout: 15_000 })
          .catch(() => {});
        // recharts' ResponsiveContainer measures its parent via ResizeObserver after
        // mount, not synchronously; screenshotting too soon after navigation can catch
        // a chart mid-measurement (tiny, corner-pinned bars), confirmed by re-rendering
        // the same page later and getting the correctly sized chart every time.
        await new Promise((r) => setTimeout(r, 1500));
        const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
        const broken = await page.evaluate(() =>
          [...document.images].filter((img) => img.complete && img.naturalWidth === 0).map((img) => img.src),
        );
        // A healthy page with demo data renders no error states.
        const errorStates = await page.evaluate(() =>
          [...document.querySelectorAll("[data-qa='error-state']")].map((el) => el.textContent?.slice(0, 80) ?? ""),
        );
        const file = path.join(OUT, `${sizeKey}-${theme}-${slug(p)}.png`);
        await page.screenshot({ path: file, fullPage: FULL });
        const issues = [...consoleErrors];
        if (overflow > 1) issues.push(`horizontal overflow ${overflow}px`);
        for (const src of broken) issues.push(`broken image ${src}`);
        for (const text of errorStates) issues.push(`error state: ${text}`);
        if (issues.length) problems.push({ page: p, theme, size: sizeKey, issues });
        console.log(`${issues.length ? "WARN" : "ok  "} ${sizeKey} ${theme} ${p}${issues.length ? `: ${issues.join(" | ")}` : ""}`);
      }
      await ctx.close();
    }
  }
  await browser.close();
  console.log(`\n${problems.length} page(s) with problems. Screenshots in ${OUT}`);
  if (problems.length) process.exitCode = 1;
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
