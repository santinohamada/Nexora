// Builds results/ui-summary.json from the Playwright JSON report(s).
// Usage: node make-summary.mjs [report.json] [previous-run-report.json]
import fs from "fs";
import path from "path";
import os from "os";
import { execSync } from "child_process";

const here = import.meta.dirname;
const reportPath = process.argv[2] ?? path.join(here, "results", "ui-results.json");
const prevPath = process.argv[3];
const catalog = JSON.parse(fs.readFileSync(path.join(here, "..", "..", "docs", "TP8", "casos_prueba.json"), "utf-8"));
const uiIds = catalog.cases.filter((c) => c.ejecucion === "ui").map((c) => c.id);

const collect = (file) => {
  const out = {};
  const walk = (suite) => {
    for (const s of suite.specs ?? []) {
      for (const t of s.tests ?? []) {
        const id = s.title.match(/^TC-LSA-\d{3}-\d{2}/)?.[0];
        if (id) out[id] = { title: s.title, test: t };
      }
    }
    (suite.suites ?? []).forEach(walk);
  };
  JSON.parse(fs.readFileSync(file, "utf-8")).suites.forEach(walk);
  return out;
};
const strip = (s) => s.replace(/\u001b\[[0-9;]*m/g, "");
const status = (t) => {
  const r = t.results.at(-1);
  if (!r || r.status === "skipped" || t.status === "skipped") return "blocked";
  return r.status === "passed" ? "pass" : "fail";
};

const cur = collect(reportPath);
const prev = prevPath && fs.existsSync(prevPath) ? collect(prevPath) : null;
const git = execSync("git rev-parse --short HEAD", { cwd: path.join(here, "..", "..") }).toString().trim();

const entries = uiIds.map((id) => {
  const c = cur[id];
  if (!c) return { id, status: "blocked", observed: "Caso no ejecutado: no hay resultado en el reporte de Playwright.", duration_ms: 0, timestamp: null };
  const r = c.test.results.at(-1);
  const ann = c.test.annotations ?? [];
  const observed = ann.filter((a) => a.type === "observed").map((a) => a.description).join(" | ");
  const chromium = ann.find((a) => a.type === "chromium")?.description;
  const st = status(c.test);
  let text = observed;
  if (st === "fail") {
    const msg = strip(r.error?.message ?? r.errors?.[0]?.message ?? "").split("\n").filter(Boolean).slice(0, 4).join(" ").slice(0, 400);
    text = `${observed}${observed ? " | " : ""}FALLA: ${msg}`;
  }
  const e = { id, status: st, observed: text || "(sin observación registrada)", duration_ms: r?.duration ?? 0, timestamp: r?.startTime ?? null };
  if (prev) {
    const p = prev[id];
    e.stable_between_runs = p ? status(p.test) === st : null;
  }
  e.environment = { git: git, chromium, os: `${os.type()} ${os.release()} (${os.platform()} ${os.arch()})` };
  return e;
});

const counts = entries.reduce((a, e) => ((a[e.status] = (a[e.status] ?? 0) + 1), a), {});
const summary = { generated_at: new Date().toISOString(), counts, flaky: entries.filter((e) => e.stable_between_runs === false).map((e) => e.id), cases: entries };
fs.writeFileSync(path.join(here, "results", "ui-summary.json"), JSON.stringify(summary, null, 2), "utf-8");
console.log(JSON.stringify(counts), "flaky:", summary.flaky.join(",") || "none");
