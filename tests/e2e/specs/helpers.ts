import { test as base, expect } from "@playwright/test";
import type { Page, BrowserContext, APIRequestContext, Route, WebSocketRoute } from "@playwright/test";
import * as path from "path";
import * as fs from "fs";
import { DatabaseSync } from "node:sqlite";

export { expect };
export const API = "http://localhost:8000";
export const ROOT = path.resolve(__dirname, "..", "..", "..");
export const RUNTIME = path.join(__dirname, "..", ".tmp", "runtime"); // backend cwd (isolated copy), see playwright.config.ts
export const DB = path.join(__dirname, "..", ".tmp", "test.db");
export const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

/** Records an observed value in the JSON report (annotation type "observed"). */
export const obs = (text: string) => base.info().annotations.push({ type: "observed", description: text });

/**
 * Per-page probes installed in every context:
 *  - __gum: number of getUserMedia calls (and __denyCamera to make them reject)
 *  - __bubbles: Date.now() of each chat bubble appearing (to compare both station faces)
 *  - __audio: spy on `new Audio(...).play()` (play is stubbed, nothing is heard)
 */
async function installProbes(context: BrowserContext) {
  await context.addInitScript(() => {
    const w = window as any;
    w.__gum = 0;
    const md = navigator.mediaDevices;
    if (md && md.getUserMedia) {
      const orig = md.getUserMedia.bind(md);
      md.getUserMedia = (c?: MediaStreamConstraints) => {
        w.__gum++;
        if (w.__denyCamera) return Promise.reject(new DOMException("Permission denied", "NotAllowedError"));
        return orig(c);
      };
    }
    w.__bubbles = [];
    let last = 0;
    const start = () =>
      new MutationObserver(() => {
        const n = document.querySelectorAll("[data-chat-message]").length;
        for (let i = last; i < n; i++) w.__bubbles.push(Date.now());
        last = n;
      }).observe(document.documentElement, { childList: true, subtree: true });
    if (document.documentElement) start();
    else document.addEventListener("DOMContentLoaded", start);
    w.__resp = [] as number[]; // Date.now() when POST /process_sentence response headers arrive
    const origFetch = window.fetch.bind(window);
    window.fetch = async (...a: Parameters<typeof fetch>) => {
      const r = await origFetch(...a);
      if (String(a[0]).includes("process_sentence")) w.__resp.push(Date.now());
      return r;
    };
    const OrigAudio = window.Audio;
    w.__audio = { created: 0, plays: [] as number[] };
    (window as any).Audio = function (src?: string) {
      const a = new OrigAudio(src);
      w.__audio.created++;
      a.play = () => {
        w.__audio.plays.push(Date.now());
        return Promise.resolve();
      };
      return a;
    };
  });
}

export const test = base.extend<{ _info: void }>({
  context: async ({ context }, use) => {
    await installProbes(context);
    await use(context);
  },
  _info: [
    async ({ browser }, use, testInfo) => {
      testInfo.annotations.push({ type: "chromium", description: browser.version() });
      await use();
    },
    { auto: true },
  ],
});

// ---------------------------------------------------------------- recognition WebSocket (simulated)
export type Prediction = { sign: string; confidence: number; top3: { sign: string; confidence: number }[] };
export const pred = (sign: string, confidence: number, top3?: { sign: string; confidence: number }[]): Prediction => ({
  sign,
  confidence,
  top3: top3 ?? [
    { sign, confidence },
    { sign: "idle", confidence: 6 },
    { sign: "cabeza", confidence: 4 },
  ],
});

export type WsMock = {
  conns: { ws: WebSocketRoute; t: number }[];
  frameCounts: number[];
  send: (p: Prediction) => void;
  closeFromServer: () => void;
  ready: () => Promise<void>;
};

/** Replaces /ws/predict with a mock server (no backend): the test injects predictions. SIMULATED recognition. */
export async function mockPredictWs(page: Page): Promise<WsMock> {
  const m: WsMock = {
    conns: [],
    frameCounts: [],
    send: (p) => m.conns[m.conns.length - 1].ws.send(JSON.stringify(p)),
    closeFromServer: () => m.conns[m.conns.length - 1].ws.close(),
    // Resolves when the camera + MediaPipe pipeline is producing frames (>= 20 frames sent).
    ready: async () => {
      await expect.poll(() => m.frameCounts.length, { timeout: 90_000, message: "pipeline de cámara sin frames" }).toBeGreaterThan(0);
    },
  };
  await page.routeWebSocket(/\/ws\/predict/, (ws) => {
    m.conns.push({ ws, t: Date.now() });
    ws.onMessage((msg) => {
      try {
        m.frameCounts.push(JSON.parse(String(msg)).frames.length);
      } catch {
        /* ignore */
      }
    });
  });
  return m;
}

const CORS = { "access-control-allow-origin": "*", "access-control-allow-headers": "*", "access-control-allow-methods": "*" };
export async function fulfillJson(route: Route, body: unknown, status = 200) {
  if (route.request().method() === "OPTIONS") return route.fulfill({ status: 204, headers: CORS });
  return route.fulfill({ status, headers: CORS, contentType: "application/json", body: JSON.stringify(body) });
}

/** Mocks POST /process_sentence (SIMULATED translation). */
export async function mockProcessSentence(page: Page, natural: string, audio = "", delayMs = 0) {
  await page.route("**/process_sentence", async (route) => {
    if (delayMs) await sleep(delayMs);
    await fulfillJson(route, { original: "x", natural_sentence: natural, audio_base64: audio, source: "template", latency_ms: 1 });
  });
}

/** Minimal valid WAV (50 ms of silence, 8 kHz mono 16 bit) as base64. */
export function tinyWav(): string {
  const n = 400;
  const b = Buffer.alloc(44 + n * 2);
  b.write("RIFF", 0);
  b.writeUInt32LE(36 + n * 2, 4);
  b.write("WAVEfmt ", 8);
  b.writeUInt32LE(16, 16);
  b.writeUInt16LE(1, 20);
  b.writeUInt16LE(1, 22);
  b.writeUInt32LE(8000, 24);
  b.writeUInt32LE(16000, 28);
  b.writeUInt16LE(2, 32);
  b.writeUInt16LE(16, 34);
  b.write("data", 36);
  b.writeUInt32LE(n * 2, 40);
  return b.toString("base64");
}

// ---------------------------------------------------------------- station faces
/** Waits until React has attached its handlers to the element (events posted before hydration would be lost). */
export async function hydrated(page: Page, selector: string) {
  await page.waitForFunction((sel) => {
    const el = document.querySelector(sel);
    return !!el && Object.keys(el).some((k) => k.startsWith("__reactProps"));
  }, selector);
  await page.waitForTimeout(300); // effects (BroadcastChannel subscription) flush right after hydration
}

export async function openPatient(context: BrowserContext, opts: { accept?: boolean; mock?: boolean; pre?: (p: Page) => Promise<void> } = {}) {
  const { accept = true, mock = true, pre } = opts;
  const page = await context.newPage();
  if (pre) await pre(page);
  const ws = mock ? await mockPredictWs(page) : null;
  await page.goto("/paciente");
  await hydrated(page, '[role="dialog"] button');
  if (accept) await page.getByRole("button", { name: "Acepto y continúo" }).click();
  return { page, ws: ws as WsMock };
}

export async function openReception(context: BrowserContext) {
  const page = await context.newPage();
  await page.goto("/recepcion");
  await expect(page.getByRole("heading", { name: "Conversación con paciente" })).toBeVisible();
  await hydrated(page, '[placeholder="Escribir..."]');
  return page;
}

/** Posts an event on BroadcastChannel("nexora-chat") from `page`; every other face of the origin receives it. */
export async function postChat(page: Page, ev: unknown) {
  await page.evaluate(async (e) => {
    const bc = new BroadcastChannel("nexora-chat");
    bc.postMessage(e);
    await new Promise((r) => setTimeout(r, 80));
    bc.close();
  }, ev);
}
export const patientMsg = (id: number, text = "Me duele la cabeza.", words = ["yo", "cabeza", "dolor"]) => ({
  type: "MESSAGE",
  payload: { id, role: "PACIENTE", text, time: "10:00", words },
});

export const bubbleBox = (page: Page, text: string) =>
  page.locator("[data-chat-message]").filter({ hasText: text }).locator("xpath=ancestor::div[contains(@class,'shadow-sm')][1]");
export const bubbleTexts = (page: Page) => page.locator("[data-chat-message]").allTextContents();
export const bubbleTimes = (page: Page): Promise<number[]> => page.evaluate(() => (window as any).__bubbles);
/** Transcript pill over the video ("yo cabeza dolor"). */
export const sentenceWindow = (page: Page) => page.locator("span.text-white.truncate");

// ---------------------------------------------------------------- backend / DB observation
export async function getMetrics(request: APIRequestContext, since?: string) {
  const r = await request.get(`${API}/metrics${since ? `?since=${encodeURIComponent(since)}` : ""}`);
  return r.json();
}
export const totalEvents = (m: any) => Object.values(m.counts as Record<string, number>).reduce((a, b) => a + b, 0);

export function dbAll(sql: string, ...params: any[]): any[] {
  const db = new DatabaseSync(DB, { readOnly: true });
  try {
    return db.prepare(sql).all(...params) as any[];
  } finally {
    db.close();
  }
}

export function externalRequests(page: Page): string[] {
  const out: string[] = [];
  page.on("request", (r) => {
    const u = r.url();
    if (/^(https?|wss?):\/\/(localhost|127\.0\.0\.1)[:/]/.test(u) || !/^(https?|wss?):/.test(u)) return;
    out.push(u);
  });
  return out;
}

export function listAudits(page: Page) {
  const out: any[] = [];
  page.on("request", (r) => {
    if (r.method() === "POST" && r.url().endsWith("/audit")) out.push(r.postDataJSON());
  });
  return out;
}

export function cleanupCaptureLabels() {
  for (const root of ["custom", "custom_blendshapes"]) {
    const dir = path.join(RUNTIME, "dataset", root);
    for (const d of fs.existsSync(dir) ? fs.readdirSync(dir) : []) {
      if (d.startsWith("zz_ui_")) fs.rmSync(path.join(dir, d), { recursive: true, force: true });
    }
  }
}

/** Browser storage of a page: key names for the report, full text (haystack) to search for conversation leaks. */
export async function storageDump(page: Page) {
  return page.evaluate(async () => {
    const ls = Object.entries(localStorage);
    const ss = Object.entries(sessionStorage);
    const idb = (await indexedDB.databases()).map((d) => d.name);
    return {
      keys: `localStorage=[${ls.map((e) => e[0]).join(",")}] sessionStorage=[${ss.map((e) => e[0].replace(/:.*/, "")).join(",")}] IndexedDB=[${idb.join(",")}] cookie=${JSON.stringify(document.cookie)}`,
      haystack: JSON.stringify([ls, ss, idb, document.cookie]),
    };
  });
}
