import * as fs from "fs";
import * as path from "path";
import { test, expect, obs, sleep, API, RUNTIME, cleanupCaptureLabels } from "./helpers";
import type { Page } from "@playwright/test";

// Capture tests write under dataset/custom/zz_ui_* (the backend's cwd is the temp runtime copy, tests/e2e/.tmp/runtime); removed before and after.
test.setTimeout(240_000);
test.beforeAll(cleanupCaptureLabels);
test.afterAll(cleanupCaptureLabels);

const chips = (page: Page) => page.locator("div.flex-wrap button");
const chip = (page: Page, label: string) => chips(page).filter({ hasText: new RegExp(`^${label}\\s*(\\(\\d+\\))?$`) });
const chipList = async (page: Page) =>
  (await chips(page).allTextContents()).map((t) => {
    const m = t.trim().match(/^(.+?)\s*(?:\((\d+)\))?$/)!;
    return { label: m[1], count: m[2] === undefined ? null : Number(m[2]) };
  });
const folder = (label: string) => path.join(RUNTIME, "dataset", "custom", label);
const npyCount = (label: string) => (fs.existsSync(folder(label)) ? fs.readdirSync(folder(label)).filter((f) => f.endsWith(".npy")).length : 0);

async function openCapture(context) {
  const page = await context.newPage();
  const reqs: any[] = [];
  const resps: { status: number; body: any }[] = [];
  page.on("request", (r) => {
    if (r.method() === "POST" && r.url().endsWith("/capture")) reqs.push(r.postDataJSON());
  });
  page.on("response", async (r) => {
    if (r.request().method() === "POST" && r.url().endsWith("/capture")) resps.push({ status: r.status(), body: await r.json().catch(() => null) });
  });
  await page.goto("/captura");
  await expect(page.getByRole("heading", { name: "Modo de Captura" })).toBeVisible();
  await expect(chip(page, "dolor")).toContainText("(");
  await page.getByLabel("Tu nombre").fill("e2e");
  return { page, reqs, resps };
}
async function addLabel(page: Page, name: string, how: "click" | "enter" = "click") {
  await page.getByRole("button", { name: "Nueva seña" }).click();
  const input = page.getByPlaceholder("Nombre de la nueva seña...");
  await input.fill(name);
  if (how === "enter") await input.press("Enter");
  else await page.getByRole("button", { name: "Agregar", exact: true }).click();
}
const start = (page: Page) => page.getByRole("button", { name: "Empezar" }).click();
const validFrames = () => Array.from({ length: 45 }, () => Array.from({ length: 75 }, () => [0, 0, 0, 0]));
const validBlendshapes = () => Array.from({ length: 45 }, () => Array.from({ length: 52 }, () => 0));
const saved = (page: Page) => page.getByText("¡Guardado!");

function npyInfo(file: string) {
  const b = fs.readFileSync(file);
  const len = b.readUInt16LE(8);
  const header = b.subarray(10, 10 + len).toString("latin1");
  return { magic: b.subarray(1, 6).toString(), descr: /'descr': '([^']+)'/.exec(header)?.[1], shape: /'shape': (\([^)]*\))/.exec(header)?.[1] };
}

test("TC-LSA-006-01 grabar una muestra con cuenta regresiva, 45 frames y guardado", async ({ context, request }) => {
  const { page, reqs, resps } = await openCapture(context);
  await expect(page.getByText("Seña a grabar:")).toBeVisible();
  await expect(page.getByRole("button", { name: "Volver a Inferencia" })).toBeVisible();
  const classes: string[] = await (await request.get(`${API}/classes`)).json();
  const stats: Record<string, number> = await (await request.get(`${API}/dataset_stats`)).json();
  const expected = [...new Set([...classes, ...Object.keys(stats)])].filter((l) => l !== "idle").sort();
  const list = await chipList(page);
  expect(list.map((c) => c.label)).toEqual(expected);
  for (const c of list) if (stats[c.label] !== undefined) expect(c.count).toBe(stats[c.label]);
  await chip(page, "dolor").click();
  await expect(page.getByText(new RegExp(String.raw`Grabando para:\s*dolor\s*\(${stats.dolor} muestras\)`))).toBeVisible();

  const L = "zz_ui_006a"; // test label instead of "dolor" so the real dataset is not altered
  await addLabel(page, L);
  await page.route("**/capture", async (route) => {
    await sleep(1000); // keeps "Procesando..." visible long enough to observe
    await route.continue();
  });
  await start(page);
  const cd = page.locator("span.text-8xl");
  const seen: number[] = [];
  for (const n of ["3", "2", "1"]) {
    await expect(cd).toHaveText(n, { timeout: 20_000 });
    seen.push(Date.now());
  }
  const steps = [seen[1] - seen[0], seen[2] - seen[1]];
  for (const d of steps) expect(d).toBeGreaterThanOrEqual(800); // nominal 1000 ms per number; the page runs slower under CPU load, so no tight upper bound
  await expect(page.getByText("GRABANDO", { exact: true })).toBeVisible({ timeout: 90_000 });
  await expect(page.getByText("Procesando...")).toBeVisible({ timeout: 90_000 });
  await expect(saved(page)).toBeVisible();
  expect(reqs).toHaveLength(1);
  const body = reqs[0];
  expect(body.label).toBe(L);
  expect(body.blendshapes).toHaveLength(45);
  expect(body.blendshapes.every((r) => r.length === 52)).toBe(true);
  expect(body.frames).toHaveLength(45);
  expect(body.frames.every((f) => f.length === 75 && f.every((lm) => lm.length === 4))).toBe(true);
  await expect.poll(() => resps.length).toBe(1);
  expect(resps[0].status).toBe(200);
  expect(resps[0].body).toMatchObject({ status: "ok", samples_for_label: 1 });
  const info = npyInfo(path.join(RUNTIME, resps[0].body.saved_to));
  expect(info).toMatchObject({ descr: "<f4", shape: "(45, 75, 4)" });
  await expect(chip(page, L)).toHaveText(`${L}(1)`);
  await page.getByRole("link", { name: "Volver a Inferencia" }).click();
  await page.goto("/captura");
  await expect(chip(page, L)).toContainText("(1)");
  obs(`Pantalla 'Modo de Captura' con 'Seña a grabar:', 'Volver a Inferencia' y ${list.length} chips ordenados [${list.map((c) => `${c.label}${c.count === null ? "" : ` (${c.count})`}`).join(", ")}] sin 'idle'; 'Grabando para: dolor (${stats.dolor} muestras)'. Se grabó con la etiqueta de prueba ${L}: cuenta regresiva 3, 2, 1 (intervalos ${steps.join(" y ")} ms), 'GRABANDO', 'Procesando...', '¡Guardado!'; POST /capture label=${body.label} frames=${body.frames.length}x75x4 blendshapes=${body.blendshapes.length}x52 -> ${resps[0].status} samples_for_label=${resps[0].body.samples_for_label}; archivo .npy ${info.descr} ${info.shape}; chip '${L} (1)' tras volver.`);
});

test("TC-LSA-006-02 varias repeticiones consecutivas y validación del campo Repeticiones", async ({ context }) => {
  const { page, reqs } = await openCapture(context);
  const L = "zz_ui_006b";
  await addLabel(page, L);
  const spin = page.getByRole("spinbutton");
  await spin.fill("3");
  await start(page);
  for (const n of [1, 2, 3]) await expect(page.getByText(`MUESTRA ${n} / 3`)).toBeVisible({ timeout: 90_000 });
  await expect(saved(page)).toBeVisible({ timeout: 90_000 });
  expect(reqs).toHaveLength(3);
  expect(reqs.every((r) => r.frames.length === 45)).toBe(true);
  await expect(chip(page, L)).toHaveText(`${L}(3)`);
  obs(`Repeticiones=3: indicador 'MUESTRA 1 / 3', 'MUESTRA 2 / 3', 'MUESTRA 3 / 3'; ${reqs.length} POST /capture con 45 frames; chip '${L} (3)'; archivos en disco: ${npyCount(L)}.`);
  await expect(page.getByRole("button", { name: "Empezar" })).toBeVisible({ timeout: 10_000 });

  await spin.fill("0");
  const v0 = await spin.inputValue();
  await spin.fill("");
  const vEmpty = await spin.inputValue();
  await spin.fill("-2");
  const vNeg = await spin.inputValue();
  const before = reqs.length;
  await start(page);
  const savedShown = await saved(page).waitFor({ timeout: 2500 }).then(() => true).catch(() => false);
  await sleep(500);
  const extra = reqs.length - before;
  obs(`Valores del campo tras escribir 0 -> '${v0}', vacío -> '${vEmpty}', -2 -> '${vNeg}'. Con -2 y 'Empezar': '¡Guardado!' mostrado=${savedShown}, peticiones POST /capture=${extra}.`);
  expect.soft(v0).toBe("1");
  expect.soft(vEmpty).toBe("1");
  expect(savedShown && extra === 0, "no debe mostrarse '¡Guardado!' sin haber guardado ninguna muestra (D-11)").toBe(false);
});

test("TC-LSA-006-03 etiqueta nueva: la carpeta se crea al guardar la primera muestra", async ({ context, request }) => {
  const { page, resps } = await openCapture(context);
  const L = "zz_ui_006c";
  await addLabel(page, L);
  await expect(chip(page, L)).toHaveClass(/bg-indigo-600/);
  await expect(page.getByText(`Grabando para: ${L}`)).toBeVisible();
  await expect(page.getByText("(nueva — la carpeta se crea al grabar)")).toBeVisible();
  expect(fs.existsSync(folder(L))).toBe(false);
  await start(page);
  await expect(saved(page)).toBeVisible({ timeout: 90_000 });
  expect(npyCount(L)).toBe(1);
  const stats = await (await request.get(`${API}/dataset_stats`)).json();
  expect(stats[L]).toBe(1);
  await expect(chip(page, L)).toHaveText(`${L}(1)`);
  obs(`Chip '${L}' seleccionado, texto 'Grabando para: ${L}' con '(nueva — la carpeta se crea al grabar)', carpeta inexistente antes; tras grabar: carpeta con ${npyCount(L)} .npy, /dataset_stats ${L}=${stats[L]}, chip '${L} (1)', respuesta ${resps[0]?.status}.`);
});

test("TC-LSA-006-04 Detener cancela la repetición en curso sin guardarla", async ({ context }) => {
  const { page, reqs } = await openCapture(context);
  const L = "zz_ui_006d";
  await addLabel(page, L);
  const cd = page.locator("span.text-8xl");
  // Step 1: stop during the countdown
  await start(page);
  await expect(cd).toBeVisible();
  await page.getByRole("button", { name: "Detener" }).click();
  const empezar = page.getByRole("button", { name: "Empezar" });
  const immediate = { empezar: await empezar.isVisible(), countdown: await cd.isVisible() };
  await sleep(1500);
  const later = { empezar: await empezar.isVisible(), countdown: await cd.isVisible(), grabando: await page.getByText("GRABANDO", { exact: true }).isVisible() };
  await sleep(6500);
  const s1at8 = { posts: reqs.length, files: npyCount(L) };
  const strayDone = await saved(page).waitFor({ timeout: 45_000 }).then(() => true).catch(() => false); // a sequence that was not aborted ends with "¡Guardado!"
  await expect(empezar).toBeVisible({ timeout: 15_000 });
  await sleep(2500);
  const s1 = { posts: reqs.length, files: npyCount(L) };
  const base = reqs.length;
  // Step 3: stop while recording
  await start(page);
  await expect(page.getByText("GRABANDO", { exact: true })).toBeVisible({ timeout: 90_000 });
  await sleep(1200);
  await page.getByRole("button", { name: "Detener" }).click();
  const tl: string[] = [];
  for (let i = 0; i < 8; i++) {
    await sleep(1000);
    tl.push(`${i + 1}s:posts=${reqs.length - base},files=${npyCount(L)},grabando=${await page.getByText("GRABANDO", { exact: true }).isVisible()},proc=${await page.getByText("Procesando...").isVisible()}`);
  }
  const s3 = { posts: reqs.length - base, frames: reqs.slice(base).map((r) => r.frames.length), files: npyCount(L) - s1.files };
  obs(`Paso 1 (Detener en cuenta regresiva): inmediatamente 'Empezar'=${immediate.empezar} y cuenta regresiva visible=${immediate.countdown}; a los 1.5 s 'Empezar'=${later.empezar}, cuenta regresiva=${later.countdown}, 'GRABANDO'=${later.grabando}; a los 8 s: POST /capture=${s1at8.posts}, archivos=${s1at8.files}; al terminar la secuencia (¡Guardado!=${strayDone}): POST /capture=${s1.posts}, archivos=${s1.files}. Paso 3 (Detener grabando a ~1.2 s): POST /capture=${s3.posts} (frames ${JSON.stringify(s3.frames)}), archivos=${s3.files}. Línea de tiempo del paso 3: ${tl.join(" ; ")}.`);
  expect.soft(s1.posts, "paso 1: no debe enviarse ninguna muestra (D-12)").toBe(0);
  expect.soft(s3.posts, "paso 3: no debe guardarse la repetición cancelada (D-12)").toBe(0);
  expect(s1.files + s3.files).toBe(0);
});

test("TC-LSA-007-02 lista combinada de etiquetas, filtro de búsqueda y alta de etiqueta válida", async ({ context, request }) => {
  for (const l of ["zz_ui_007a", "zz_ui_007b", "zz_ui_007c"]) {
    const r = await request.post(`${API}/capture`, { data: { label: l, recorder: "e2e", frames: validFrames(), blendshapes: validBlendshapes() } }); // test data setup
    expect(r.status()).toBe(200);
  }
  const { page } = await openCapture(context);
  const classes: string[] = await (await request.get(`${API}/classes`)).json();
  const stats: Record<string, number> = await (await request.get(`${API}/dataset_stats`)).json();
  const expected = [...new Set([...classes, ...Object.keys(stats)])].filter((l) => l !== "idle").sort();
  const list = await chipList(page);
  expect(list.map((c) => c.label)).toEqual(expected);
  expect(list.length).toBeGreaterThan(6);
  const search = page.getByPlaceholder("Buscar seña...");
  await expect(search).toBeVisible();
  expect(list.find((c) => c.label === "zz_ui_007a")?.count).toBe(1);
  await search.fill("zz_ui");
  const filtered = (await chipList(page)).map((c) => c.label);
  expect(filtered).toEqual(expected.filter((l) => l.includes("zz_ui")));
  await addLabel(page, "ZZ_UI_Nueva", "enter");
  await expect(chip(page, "zz_ui_nueva")).toHaveClass(/bg-indigo-600/);
  await search.fill("");
  await addLabel(page, "dolor", "enter");
  await expect(chip(page, "dolor")).toHaveCount(1);
  await expect(chip(page, "dolor")).toHaveClass(/bg-indigo-600/);
  await expect(page.getByText(/Grabando para: dolor/)).toBeVisible();
  obs(`Lista = unión de /classes y /dataset_stats ordenada, sin 'idle' (${list.length} etiquetas), campo 'Buscar seña...' visible; filtro 'zz_ui' deja [${filtered.join(", ")}]; 'ZZ_UI_Nueva' crea y selecciona 'zz_ui_nueva'; repetir 'dolor' no duplica el chip y lo selecciona.`);
});

test("TC-LSA-007-03 etiquetas con formato inválido se rechazan y no hay falso guardado", async ({ context }) => {
  const { page, reqs, resps } = await openCapture(context);
  const invalid = ["fiebre alta", "dolor!", "a".repeat(33)];
  const out: string[] = [];
  let accepted = 0;
  for (const name of invalid) {
    const before = reqs.length;
    await addLabel(page, name);
    const chipShown = (await chipList(page)).some((c) => c.label === name);
    const msg = await page.getByText(/minúscula|formato|inválid|no válid|caracteres permitidos/i).count();
    out.push(`'${name.length > 12 ? name.slice(0, 8) + "...(33)" : name}': chip agregado=${chipShown}, mensaje de formato=${msg > 0}`);
    if (!chipShown) continue;
    accepted++;
    await start(page);
    await page.getByText(/¡Guardado!|No se pudo|error/i).first().waitFor({ timeout: 90_000 });
    const guardado = await saved(page).isVisible();
    await expect(page.getByRole("button", { name: "Empezar" })).toBeVisible({ timeout: 15_000 });
    const st = resps[resps.length - 1]?.status;
    out.push(`  grabación: POST /capture=${reqs.length - before}, HTTP ${st}, '¡Guardado!' mostrado=${guardado}`);
  }
  obs(out.join(" | "));
  expect(accepted, "las etiquetas inválidas deben rechazarse con un mensaje de formato (D-11)").toBe(0);
});
