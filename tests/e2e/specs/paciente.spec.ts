import AxeBuilder from "@axe-core/playwright";
import {
  test, expect, obs, sleep, pred, mockPredictWs, mockProcessSentence, tinyWav, openPatient, openReception,
  postChat, patientMsg, bubbleBox, bubbleTexts, bubbleTimes, sentenceWindow, getMetrics, listAudits,
  externalRequests, storageDump, API,
} from "./helpers";

test.setTimeout(150_000);

const accept = (page) => page.getByRole("button", { name: "Acepto y continúo" }).click();
const LIVE = "EN VIVO · Visión por computadora";

test("TC-LSA-001-03 captura de cámara y envío periódico de frames al WebSocket", async ({ page }) => {
  const msgs: { frames: number; ok: boolean }[] = [];
  let wsUrl = "";
  page.on("websocket", (ws) => {
    if (!ws.url().includes("/ws/predict")) return;
    wsUrl = ws.url();
    ws.on("framesent", (f) => {
      if (typeof f.payload !== "string") return;
      try {
        const fr: number[][][] = JSON.parse(f.payload).frames;
        msgs.push({
          frames: fr.length,
          ok: fr.every((fm) => fm.length === 75 && fm.every((lm) => lm.length === 4 && lm.every(Number.isFinite))),
        });
      } catch {
        /* not a frames message */
      }
    });
  });
  await page.goto("/paciente");
  await accept(page);
  await expect(page.getByText("Activando cámara...")).toBeHidden({ timeout: 60_000 });
  const cam = await page.evaluate(() => {
    const v = document.querySelector("video") as HTMLVideoElement;
    const s = v.srcObject as MediaStream | null;
    return { isStream: s instanceof MediaStream, live: !!s && s.getVideoTracks().some((t) => t.readyState === "live"), canvas: !!document.querySelector("canvas") };
  });
  expect(cam).toEqual({ isStream: true, live: true, canvas: true });
  await expect(page.getByText(LIVE)).toBeVisible();
  await expect.poll(() => msgs.length, { timeout: 90_000 }).toBeGreaterThan(0);
  await sleep(10_000);
  // Under CPU load the frame rate is low: keep collecting (up to 60 s more) until the cap of 45 is visible.
  await expect.poll(() => Math.max(...msgs.map((m) => m.frames)), { timeout: 60_000 }).toBeGreaterThanOrEqual(45);
  const counts = msgs.map((m) => m.frames);
  obs(`WebSocket ${wsUrl}; ${counts.length} mensajes en la ventana; frames por mensaje: [${counts.slice(0, 12).join(", ")}]; landmarks por frame y números por landmark correctos: ${msgs.every((m) => m.ok)}`);
  expect(wsUrl).toContain("/ws/predict?v=1");
  expect(counts[0]).toBe(20);
  expect(Math.max(...counts)).toBeLessThanOrEqual(45);
  for (let i = 1; i < counts.length; i++) expect(counts[i]).toBeGreaterThanOrEqual(Math.min(counts[i - 1] + 8, 45));
  expect(msgs.every((m) => m.ok)).toBe(true);
});

test("TC-LSA-001-04 umbral de confianza, idle y repeticiones consecutivas (predicciones simuladas)", async ({ context }) => {
  // No consent on purpose: without camera frames the sentence never closes by stillness, so the transcript can be read at leisure.
  const { page, ws } = await openPatient(context, { accept: false });
  await expect.poll(() => ws.conns.length).toBe(1);
  const win = sentenceWindow(page);
  const sign0 = page.locator("#pred-sign-0");
  const conf0 = page.locator("#pred-conf-0");

  ws.send(pred("dolor", 65, [{ sign: "dolor", confidence: 65 }, { sign: "cabeza", confidence: 20 }, { sign: "yo", confidence: 15 }]));
  await expect(conf0).toHaveText("65.0%");
  await expect(sign0).toHaveText("dolor");
  await expect(page.locator("#pred-bar-0")).toHaveAttribute("style", /width:\s*65%/);
  await expect(win).toHaveCount(0);

  ws.send(pred("dolor", 90, [{ sign: "dolor", confidence: 90 }, { sign: "idle", confidence: 60 }, { sign: "cabeza", confidence: 5 }]));
  await expect(conf0).toHaveText("90.0%");
  await expect(win).toHaveCount(0);

  ws.send(pred("idle", 95, [{ sign: "idle", confidence: 95 }, { sign: "dolor", confidence: 3 }, { sign: "cabeza", confidence: 2 }]));
  await expect(sign0).toHaveText("idle");
  await expect(conf0).toHaveText("95.0%");
  await expect(win).toHaveCount(0);

  ws.send(pred("dolor", 70.0, [{ sign: "dolor", confidence: 70 }, { sign: "yo", confidence: 20 }, { sign: "cabeza", confidence: 10 }]));
  await expect(conf0).toHaveText("70.0%");
  await expect(win).toHaveText("dolor");

  ws.send(pred("dolor", 90));
  await expect(conf0).toHaveText("90.0%");
  await expect(win).toHaveText("dolor");
  ws.send(pred("cabeza", 90));
  await expect(win).toHaveText("dolor cabeza");
  ws.send(pred("dolor", 90));
  await expect(win).toHaveText("dolor cabeza dolor");
  obs("Predicciones simuladas por WebSocket. Pasos 1-3: barras actualizadas y ventana de oración ausente; paso 4 (70.0): 'dolor' agregada (umbral inclusivo); paso 5: secuencia 'dolor cabeza dolor' sin duplicar la repetición consecutiva. Se probó sin consentimiento de cámara para que la oración no se cierre por quietud.");
});

test("TC-LSA-001-05 cierre de oración por idle y burbuja automática en ambas caras", async ({ context }) => {
  const { page: p2, ws } = await openPatient(context);
  const p3 = await openReception(context);
  const calls: { t: number; body: string | null }[] = [];
  await p2.route("**/process_sentence", async (route) => {
    calls.push({ t: Date.now(), body: route.request().postData() });
    await sleep(600); // lets the intermediate "Generando respuesta de IA..." state be observed; backend is real
    await route.continue();
  });
  await ws.ready();
  for (const s of ["yo", "cabeza", "dolor"]) {
    ws.send(pred(s, 90));
    await sleep(100);
  }
  await expect(sentenceWindow(p2)).toHaveText("yo cabeza dolor");
  await sleep(2000); // a pause between signs must not close the sentence
  expect(calls.length).toBe(0);
  ws.send(pred("idle", 69)); // below the confidence threshold: still open
  await sleep(300);
  expect(calls.length).toBe(0);
  const lastT = Date.now();
  ws.send(pred("idle", 95));
  await expect.poll(() => calls.length, { timeout: 10_000 }).toBe(1);
  const gap = calls[0].t - lastT;
  expect(JSON.parse(calls[0].body!)).toEqual({ words: "yo cabeza dolor" });
  await expect(p2.getByText("Generando respuesta de IA...")).toBeVisible();
  const buttons = await p2.getByRole("button").allTextContents();
  expect(buttons.filter((b) => /confirm|enviar|aceptar|^ok$/i.test(b.trim()))).toEqual([]);
  await expect(bubbleBox(p2, "Me duele la cabeza.").locator("xpath=ancestor::div[contains(@class,'justify-end')][1]")).toBeVisible();
  await expect(bubbleBox(p3, "Me duele la cabeza.").locator("xpath=ancestor::div[contains(@class,'justify-start')][1]")).toBeVisible();
  await expect(sentenceWindow(p2)).toHaveCount(0);
  const [t2, t3] = [(await bubbleTimes(p2))[0], (await bubbleTimes(p3))[0]];
  obs(`Predicciones simuladas yo/cabeza/dolor (100 ms). POST /process_sentence ${gap} ms después de la última predicción, cuerpo {"words":"yo cabeza dolor"}; botones visibles en P-02 durante el proceso: [${buttons.map((b) => b.trim()).join(" | ")}]; burbuja PACIENTE "Me duele la cabeza." en ambas caras, diferencia entre caras ${Math.abs(t3 - t2)} ms.`);
  expect(Math.abs(t3 - t2)).toBeLessThan(500);
});

test("TC-LSA-001-06 reconexión automática del WebSocket cada 2 s sin errores visibles", async ({ context }) => {
  const { page, ws } = await openPatient(context);
  await mockProcessSentence(page, "NO_CLARO");
  await ws.ready();
  const tClose = Date.now();
  ws.closeFromServer();
  await sleep(500);
  const during = await page.evaluate(() => {
    const v = document.querySelector("video") as HTMLVideoElement;
    const s = v.srcObject as MediaStream | null;
    return { live: !!s && s.getVideoTracks().some((t) => t.readyState === "live"), text: document.body.innerText };
  });
  await expect.poll(() => ws.conns.length, { timeout: 10_000 }).toBe(2);
  const dt = ws.conns[1].t - tClose;
  obs(`Cierre desde el servidor simulado; nuevo intento de conexión ${dt} ms después; durante el corte el video sigue activo: ${during.live}; mensaje de error/desconexión en la página: ${/error|desconect|sin conexi|no se pudo|reconect/i.test(during.text)}`);
  expect(dt).toBeGreaterThanOrEqual(1800);
  expect(dt).toBeLessThanOrEqual(3000);
  expect(during.live).toBe(true);
  expect(during.text).not.toMatch(/error|desconect|sin conexi|no se pudo|reconect/i);
  ws.send(pred("dolor", 90));
  await expect(sentenceWindow(page)).toHaveText("dolor");
});

test("TC-LSA-001-07 respuesta NO_CLARO: sin burbuja y sin evento translation_displayed", async ({ context }) => {
  const { page, ws } = await openPatient(context);
  const audits = listAudits(page);
  await mockProcessSentence(page, "NO_CLARO", "", 800); // SIMULATED translation response
  await ws.ready();
  ws.send(pred("dolor", 90));
  ws.send(pred("idle", 95)); // sentences close on a confident idle
  await expect(page.getByText("Generando respuesta de IA...")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText("Generando respuesta de IA...")).toBeHidden();
  await expect(page.getByText("La conversación aparecerá aquí")).toBeVisible();
  await sleep(500);
  expect(await bubbleTexts(page)).toEqual([]);
  const translated = audits.filter((a) => a.type === "translation_displayed");
  obs(`Respuesta simulada NO_CLARO: 'Generando respuesta de IA...' apareció y desapareció; panel 'La conversación aparecerá aquí'; eventos translation_displayed enviados: ${translated.length}`);
  expect(translated).toEqual([]);
});

test("TC-LSA-001-09 página de inicio y navegación a cada estación", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Bienvenido a Nexora" })).toBeVisible();
  await expect(page.getByRole("link", { name: /Estación del Paciente/ })).toBeVisible();
  await expect(page.getByRole("link", { name: /Estación de Recepción/ })).toBeVisible();
  const logoAlt = await page.locator("main img").first().getAttribute("alt");
  await page.getByRole("link", { name: /Estación del Paciente/ }).click();
  await expect(page).toHaveURL(/\/paciente$/);
  await expect(page.getByRole("dialog")).toBeVisible();
  expect(await page.evaluate(() => (window as any).__gum)).toBe(0);
  await page.goto("/");
  await page.getByRole("link", { name: /Estación de Recepción/ }).click();
  await expect(page).toHaveURL(/\/recepcion$/);
  await expect(page.getByRole("heading", { name: "Conversación con paciente" })).toBeVisible();
  obs(`Título 'Bienvenido a Nexora', tarjetas 'Estación del Paciente' y 'Estación de Recepción'; logo con texto alternativo '${logoAlt}' (marca Nexora, D-19); /paciente muestra el diálogo sin activar la cámara.`);
});

test("TC-LSA-003-04 texto antes que audio (ventana de 1000 ms) y sin audio no se reproduce", async ({ context }) => {
  const { page, ws } = await openPatient(context);
  const mode = { audio: tinyWav() };
  await page.route("**/process_sentence", async (route) => {
    if (route.request().method() === "OPTIONS") return route.continue();
    const resp = await route.fetch(); // real backend text; audio replaced by a minimal WAV / empty (simulated)
    const j = await resp.json();
    j.audio_base64 = mode.audio;
    await route.fulfill({ response: resp, json: j });
  });
  await ws.ready();
  const speak = async () => {
    for (const s of ["yo", "cabeza", "dolor"]) {
      ws.send(pred(s, 90));
      await sleep(100);
    }
    ws.send(pred("idle", 95)); // sentences close on a confident idle
  };
  await speak();
  await expect.poll(async () => (await page.evaluate(() => (window as any).__audio.plays)).length, { timeout: 20_000 }).toBe(1);
  const a1 = await page.evaluate(() => ({ b: (window as any).__bubbles[0], p: (window as any).__audio.plays[0], r: (window as any).__resp[0] }));
  const delta = a1.p - a1.b;
  const sinceResponse = a1.p - a1.r;
  const renderLag = a1.b - a1.r;
  expect(delta).toBeGreaterThanOrEqual(900);
  expect(delta).toBeLessThanOrEqual(1500);
  // Without audio
  mode.audio = "";
  const before = await page.evaluate(() => ({ n: (window as any).__bubbles.length, c: (window as any).__audio.created }));
  await speak();
  await expect.poll(async () => (await page.evaluate(() => (window as any).__bubbles)).length, { timeout: 20_000 }).toBe(before.n + 1);
  await sleep(1800);
  const after = await page.evaluate(() => ({ c: (window as any).__audio.created, p: (window as any).__audio.plays.length }));
  obs(`Predicciones y audio simulados. Con audio: play() ${delta} ms después de mostrarse la burbuja (${sinceResponse} ms después de recibir la respuesta; la burbuja se pintó ${renderLag} ms después de la respuesta); con audio_base64 vacío: burbuja mostrada, Audio creados ${after.c - before.c}, reproducciones nuevas ${after.p - 1}.`);
  expect(after.c).toBe(before.c);
  expect(after.p).toBe(1);
});

test("TC-LSA-009-01 el diálogo de consentimiento bloquea la cámara hasta aceptar y se audita", async ({ page, request }) => {
  const before = await getMetrics(request);
  await page.goto("/paciente");
  const dlg = page.getByRole("dialog");
  await expect(dlg).toHaveAttribute("aria-modal", "true");
  await expect(dlg.getByRole("heading", { name: "Consentimiento para usar la cámara" })).toBeVisible();
  await expect(dlg).toContainText("Usamos tu cámara solo para reconocer tus señas y traducirlas a texto y voz. No se guarda ningún video ni imagen: el procesamiento ocurre en este dispositivo.");
  await expect(dlg.getByRole("button", { name: "No acepto" })).toBeVisible();
  await expect(dlg.getByRole("button", { name: "Acepto y continúo" })).toBeVisible();
  await expect(dlg).toBeFocused();
  expect(await page.evaluate(() => (window as any).__gum)).toBe(0);
  await expect(page.locator("main[inert]")).toHaveCount(1);
  const clickable = await page.getByRole("button", { name: "Limpiar Historial" }).click({ timeout: 1500 }).then(() => true).catch(() => false);
  expect(clickable).toBe(false);
  const auditReq = page.waitForRequest((r) => r.url().endsWith("/audit"));
  const auditRes = page.waitForResponse((r) => r.url().endsWith("/audit"));
  await accept(page);
  const req = await auditReq;
  expect(req.postDataJSON()).toEqual({ type: "consent", station: "paciente", consent: "accepted" });
  const res = await auditRes;
  expect(res.status()).toBe(200);
  expect(await res.json()).toEqual({ status: "ok" });
  await expect(dlg).toHaveCount(0);
  await expect(page.getByText(LIVE)).toBeVisible();
  await expect.poll(() => page.evaluate(() => (window as any).__gum), { timeout: 60_000 }).toBe(1);
  const after = await getMetrics(request);
  expect(after.consent.accepted - (before.consent.accepted ?? 0)).toBe(1);
  obs(`Diálogo role=dialog aria-modal=true con título, texto y botones 'No acepto'/'Acepto y continúo', foco en el diálogo, main con atributo inert, clic en 'Ajustes (Modo Captura)' bloqueado, getUserMedia 0 antes y 1 después de aceptar; POST /audit ${JSON.stringify(req.postDataJSON())} -> 200 {"status":"ok"}; consent.accepted +1 en /metrics.`);
});

test("TC-LSA-009-02 rechazo del consentimiento y opción de reconsiderar", async ({ page, request }) => {
  const before = await getMetrics(request);
  await page.goto("/paciente");
  const dlg = page.getByRole("dialog");
  const audit = page.waitForRequest((r) => r.url().endsWith("/audit"));
  await dlg.getByRole("button", { name: "No acepto" }).click();
  expect((await audit).postDataJSON()).toEqual({ type: "consent", station: "paciente", consent: "declined" });
  await expect(dlg).toContainText("El traductor necesita la cámara para funcionar. Podés reconsiderar cuando quieras.");
  await expect(dlg.getByRole("button")).toHaveText(["Reconsiderar"]);
  expect(await page.evaluate(() => (window as any).__gum)).toBe(0);
  await expect(page.locator("main[inert]")).toHaveCount(1);
  await dlg.getByRole("button", { name: "Reconsiderar" }).click();
  await expect(dlg.getByRole("button", { name: "No acepto" })).toBeVisible();
  await expect(dlg.getByRole("button", { name: "Acepto y continúo" })).toBeVisible();
  await accept(page);
  await expect.poll(() => page.evaluate(() => (window as any).__gum), { timeout: 60_000 }).toBe(1);
  await sleep(500);
  const after = await getMetrics(request);
  const d = { accepted: after.consent.accepted - (before.consent.accepted ?? 0), declined: after.consent.declined - (before.consent.declined ?? 0) };
  obs(`Tras 'No acepto': mensaje 'El traductor necesita la cámara para funcionar. Podés reconsiderar cuando quieras.', único botón 'Reconsiderar', getUserMedia 0, página inerte, POST /audit consent=declined. Tras reconsiderar y aceptar: getUserMedia 1. Variación de /metrics consent: ${JSON.stringify(d)}.`);
  expect(d).toEqual({ accepted: 1, declined: 1 });
});

test("TC-LSA-009-03 permiso de cámara denegado por el navegador tras consentir", async ({ context }) => {
  const { page, ws } = await openPatient(context, { pre: (p) => p.addInitScript(() => ((window as any).__denyCamera = true)) });
  await expect(page.getByText("Activando cámara...")).toBeHidden({ timeout: 60_000 }); // status "error"
  await sleep(5000);
  const mainText = await page.locator("main").innerText();
  const gum = await page.evaluate(() => (window as any).__gum);
  const hasVideo = await page.evaluate(() => !!(document.querySelector("video") as HTMLVideoElement).srcObject);
  // Expected per casos_prueba.json: an explicit camera error ("No se pudo acceder a la cámara.") or any role=alert element.
  const errEl = page.getByText("No se pudo acceder a la cámara.").or(page.getByRole("alert").filter({ hasText: /\S/ }));
  const msg = (await errEl.count()) ? await errEl.first().innerText() : null;
  obs(`getUserMedia rechazado (NotAllowedError) con ${gum} llamada(s); 'Activando cámara...' ya no se muestra; video sin stream: ${!hasVideo}; frames enviados al backend: ${ws.frameCounts.length}; mensaje de error visible para el paciente: ${msg ?? "ninguno"}; el indicador '${LIVE}' sigue visible: ${mainText.includes(LIVE)}.`);
  expect(ws.frameCounts.length).toBe(0);
  expect(msg, "el sistema debe informar el error de cámara al paciente").not.toBeNull();
});

test("TC-LSA-009-04 el consentimiento persiste al recargar y recepción abre la cámara", async ({ page, context }) => {
  await page.goto("/paciente");
  await accept(page);
  await expect.poll(() => page.evaluate(() => (window as any).__gum), { timeout: 60_000 }).toBe(1);
  await page.reload();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect.poll(() => page.evaluate(() => (window as any).__gum), { timeout: 60_000 }).toBe(1);
  const store = await storageDump(page);
  expect(store.haystack).toContain("nexora-camera-consent");
  obs(`Tras recargar: sin diálogo y getUserMedia 1. ${store.keys}.`);
  const p3 = await context.newPage();
  await p3.goto("/recepcion");
  await expect.poll(() => p3.evaluate(() => (window as any).__gum), { timeout: 60_000 }).toBe(1);
});

test("TC-LSA-014-04 latencia percibida e2e_ms y sincronización entre caras (predicciones simuladas)", async ({ context, request }) => {
  const { page: p2, ws } = await openPatient(context);
  const p3 = await openReception(context);
  const e2e: number[] = [];
  p2.on("request", (r) => {
    if (r.method() === "POST" && r.url().endsWith("/audit")) {
      const j = r.postDataJSON();
      if (j.type === "translation_displayed") e2e.push(j.e2e_ms);
    }
  });
  const combos = [
    ["yo", "cabeza", "dolor"], ["cabeza", "dolor"], ["yo", "dolor"], ["yo", "respirar"], ["dolor", "respirar"],
    ["cabeza", "respirar"], ["yo", "cabeza"], ["dolor", "respirar", "yo"], ["cabeza", "dolor", "respirar"], ["yo", "cabeza", "dolor", "respirar"],
  ];
  await ws.ready();
  const since = new Date(Date.now() - 2000).toISOString().replace("Z", "");
  for (let i = 0; i < combos.length; i++) {
    for (const s of combos[i]) {
      ws.send(pred(s, 90));
      await sleep(100);
    }
    ws.send(pred("idle", 95)); // sentences close on a confident idle
    await expect.poll(async () => (await bubbleTexts(p2)).length, { timeout: 30_000 }).toBe(i + 1);
    await expect.poll(async () => (await bubbleTexts(p3)).length, { timeout: 5_000 }).toBe(i + 1);
    await expect.poll(() => e2e.length, { timeout: 5_000 }).toBe(i + 1);
    await sleep(300);
  }
  const t2 = await bubbleTimes(p2);
  const t3 = await bubbleTimes(p3);
  const diffs = t2.map((t, i) => Math.abs(t3[i] - t));
  const sorted = [...e2e].sort((a, b) => a - b);
  const q = (p: number) => sorted[Math.min(sorted.length - 1, Math.max(0, Math.ceil((p / 100) * sorted.length) - 1))];
  const m = await getMetrics(request, since);
  const mc = m.latency_ms?.e2e_ms?.count;
  const srv = m.latency_ms?.total_ms;
  obs(`10 combinaciones con plantilla (backend real, predicciones simuladas). e2e_ms p50=${q(50).toFixed(0)} p95=${q(95).toFixed(0)} max=${sorted[sorted.length - 1].toFixed(0)} (valores: ${e2e.map((x) => x.toFixed(0)).join(", ")}); diferencia entre caras (ms): ${diffs.join(", ")}; /metrics e2e_ms count=${mc}; tiempo total del servidor (total_ms) p50=${srv?.p50} p95=${srv?.p95}.`);
  expect(q(50)).toBeLessThanOrEqual(600);
  expect(q(95)).toBeLessThanOrEqual(1000);
  expect(diffs.filter((d) => d <= 200).length / diffs.length).toBeGreaterThanOrEqual(0.95);
  expect(mc).toBe(10);
});

test("TC-LSA-015-06 el flujo crítico de P-02 opera sin Internet", async ({ page, context }) => {
  const attempted = externalRequests(page);
  await context.route(/^https?:\/\/(?!localhost[:/]|127\.0\.0\.1[:/])/, (r) => r.abort("internetdisconnected")); // emulates no Internet
  let framesSent = 0;
  let wsOpened = false;
  page.on("websocket", (ws) => {
    if (!ws.url().includes("/ws/predict")) return;
    wsOpened = true;
    ws.on("framesent", (f) => {
      if (typeof f.payload === "string" && f.payload.startsWith('{"frames"')) framesSent++;
    });
  });
  await page.goto("/paciente");
  await accept(page);
  // First frame needs the local MediaPipe warm-up (software rendering is slow): wait for it instead of a fixed 15 s.
  await expect.poll(() => framesSent, { timeout: 60_000 }).toBeGreaterThan(0).catch(() => {});
  await sleep(2_000);
  const hosts = [...new Set(attempted.map((u) => new URL(u).host))];
  const loading = await page.getByText("Activando cámara...").isVisible();
  obs(`Sin Internet (peticiones externas abortadas): intentos a hosts externos: ${attempted.length} (${hosts.join(", ") || "ninguno"}); '${"Activando cámara..."}' sigue visible: ${loading}; conexión /ws/predict abierta: ${wsOpened}; mensajes de frames enviados: ${framesSent}.`);
  expect(attempted, "no debe haber peticiones a hosts externos").toEqual([]);
  expect(loading).toBe(false);
  expect(framesSent, "la cámara debe enviar frames sin Internet").toBeGreaterThan(0);
  expect(framesSent).toBeGreaterThan(0);
});

test("TC-LSA-015-08 accesibilidad básica con axe-core (critical/serious)", async ({ context }) => {
  const { page, ws } = await openPatient(context, { accept: false });
  const report: string[] = [];
  const scan = async (label: string, p = page) => {
    const r = await new AxeBuilder({ page: p }).exclude("nextjs-portal").analyze();
    const bad = r.violations.filter((v) => v.impact === "critical" || v.impact === "serious");
    report.push(`${label}: ${bad.length ? bad.map((v) => `${v.id}[${v.impact}] x${v.nodes.length}`).join(", ") : "0 violaciones"}`);
    return bad.length;
  };
  let total = 0;
  const home = await context.newPage();
  await home.goto("/");
  total += await scan("/", home);
  total += await scan("/paciente con diálogo");
  await accept(page);
  await expect(page.getByText(LIVE)).toBeVisible();
  total += await scan("/paciente tras aceptar");
  const p3 = await openReception(context);
  total += await scan("/recepcion", p3);
  const cap = await context.newPage();
  await cap.goto("/captura");
  await expect(cap.getByText("Modo de Captura")).toBeVisible();
  total += await scan("Modo Captura", cap);
  expect(total, report.join(" | ")).toBe(0);
  obs(report.join(" | "));
  void ws;
});
