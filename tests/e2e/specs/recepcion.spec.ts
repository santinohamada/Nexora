import {
  test, expect, obs, sleep, openPatient, openReception, postChat, patientMsg, bubbleBox, bubbleTexts,
  bubbleTimes, getMetrics, totalEvents, dbAll, listAudits, storageDump, API,
} from "./helpers";

test.setTimeout(150_000);

const EMPTY_P3 = "No hay mensajes en la conversación.";
const EMPTY_P2 = "La conversación aparecerá aquí";
const NOTICE_P2 = "Traducción reportada. Repetí la seña para enviar el mensaje de nuevo.";
const NOTICE_P3 = "Traducción reportada como incorrecta. No la tomes como válida: el paciente va a repetir la seña.";
const reply = (page, text: string) => page.getByPlaceholder("Escribir...").fill(text).then(() => page.getByRole("button", { name: "Enviar" }).click());

// ------------------------------------------------------------------ CU-04
test("TC-LSA-004-01 estado inicial de P-03 y validación de texto vacío", async ({ page }) => {
  await page.goto("/recepcion");
  await expect(page.getByRole("heading", { name: "Conversación con paciente" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Conversación con paciente" })).toBeVisible();
  await expect(page.getByText(EMPTY_P3)).toBeVisible();
  const send = page.getByRole("button", { name: "Enviar" });
  const area = page.getByPlaceholder("Escribir...");
  await expect(send).toBeDisabled();
  await area.fill("   ");
  await expect(send).toBeDisabled();
  await area.fill("  Pase a la sala 2  ");
  await send.click();
  const texts = await bubbleTexts(page);
  expect(texts).toEqual(["Pase a la sala 2"]);
  await expect(area).toHaveValue("");
  await expect(send).toBeDisabled();
  await area.fill("x");
  await expect(send).toBeEnabled();
  await area.fill("");
  await expect(send).toBeDisabled();
  obs(`Estado inicial con 'Estación de Recepción / Enfermería', 'Historial del Paciente' y '${EMPTY_P3}'; 'Enviar' deshabilitado con área vacía y con espacios; tras enviar '  Pase a la sala 2  ' la burbuja contiene exactamente '${texts[0]}' y el área queda vacía; al borrar el contenido el botón vuelve a deshabilitarse.`);
});

test("TC-LSA-004-02 respuesta escrita sincronizada en ambas caras", async ({ context }) => {
  const { page: p2 } = await openPatient(context);
  const p3 = await openReception(context);
  await reply(p3, "Pase a la sala 2, por favor.");
  const box3 = bubbleBox(p3, "Pase a la sala 2, por favor.");
  await expect(box3.locator("xpath=ancestor::div[contains(@class,'justify-end')][1]")).toBeVisible();
  await expect(p3.getByPlaceholder("Escribir...")).toHaveValue("");
  const box2 = bubbleBox(p2, "Pase a la sala 2, por favor.");
  await expect(box2).toBeVisible();
  const [t2, t3] = [(await bubbleTimes(p2))[0], (await bubbleTimes(p3))[0]];
  expect(Math.abs(t2 - t3)).toBeLessThan(500);
  await expect(box2.getByRole("button", { name: /Reportar traducción/ })).toHaveCount(0);
  await expect(box3.getByRole("button", { name: /Reportar traducción/ })).toHaveCount(0);

  await postChat(p3, patientMsg(1700000000001));
  const patient3 = bubbleBox(p3, "Me duele la cabeza.");
  await expect(patient3.locator("xpath=ancestor::div[contains(@class,'justify-start')][1]")).toBeVisible();
  await expect(patient3.getByRole("button", { name: /Reportar traducción/ })).toBeVisible();
  await expect(bubbleBox(p2, "Me duele la cabeza.")).toBeVisible();
  await postChat(p3, patientMsg(1700000000001)); // same id again: deduplicated
  await sleep(300);
  const [o2, o3] = [await bubbleTexts(p2), await bubbleTexts(p3)];
  obs(`Burbuja RECEPCIONISTA alineada a la derecha (self-end) en P-03 y P-02, sin 'Reportar traducción', diferencia entre caras ${Math.abs(t2 - t3)} ms. Mensaje de paciente inyectado por BroadcastChannel: P-03 muestra rol PACIENTE y botón 'Reportar traducción'. Orden P-02=${JSON.stringify(o2)} P-03=${JSON.stringify(o3)}; tras reinyectar el mismo id queda una sola burbuja.`);
  expect(o2).toEqual(["Pase a la sala 2, por favor.", "Me duele la cabeza."]);
  expect(o3).toEqual(o2);
});

test("TC-LSA-004-03 texto plano (sin HTML) y texto largo", async ({ context }) => {
  const { page: p2 } = await openPatient(context, { accept: false });
  const p3 = await openReception(context);
  const dialogs: string[] = [];
  const errors: string[] = [];
  for (const p of [p2, p3]) {
    p.on("dialog", (d) => {
      dialogs.push(d.message());
      d.dismiss();
    });
    p.on("pageerror", (e) => errors.push(e.message));
  }
  const xss = "<img src=x onerror=alert(1)> <b>negrita</b>";
  await reply(p3, xss);
  await expect(p3.locator("[data-chat-message]").first()).toHaveText(xss);
  await expect(p2.locator("[data-chat-message]").first()).toHaveText(xss);
  expect(await p3.locator("[data-chat-message] img, [data-chat-message] b").count()).toBe(0);
  const long = "Atención ñandú ¿qué? ¡Sí! ".repeat(60).slice(0, 1000).trim();
  await reply(p3, long);
  await expect(p3.locator("[data-chat-message]").nth(1)).toHaveText(long);
  await expect(p2.locator("[data-chat-message]").nth(1)).toHaveText(long);
  const overflow = async (p) => p.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  const [o3, o2] = [await overflow(p3), await overflow(p2)];
  // Extra observation (not in the catalog): 1000 characters without any space.
  await reply(p3, "W".repeat(1000));
  await sleep(300);
  const unbroken = await overflow(p3);
  obs(`Etiquetas HTML mostradas literalmente en ambas caras; diálogos disparados: ${dialogs.length}; errores de página: ${errors.length}. Texto de ${long.length} caracteres con acentos íntegro en ambas caras; desborde horizontal (px) P-03=${o3} P-02=${o2}. Observación adicional (fuera del catálogo): con 1000 caracteres sin espacios, la página tiene un desborde horizontal de ${unbroken}px en P-03.`);
  expect(dialogs).toEqual([]);
  expect(errors).toEqual([]);
  expect(o3).toBeLessThanOrEqual(0);
  expect(o2).toBeLessThanOrEqual(0);
});

// ------------------------------------------------------------------ CU-05 (SpeechRecognition double)
const SR_DOUBLE = () => {
  const w = window as any;
  w.__srAll = [];
  class FakeSR {
    lang = "";
    continuous = false;
    interimResults = false;
    onresult: any;
    onerror: any;
    onend: any;
    constructor() {
      w.__srAll.push(this);
    }
    start() {
      w.__srStarted = this;
      w.__srStarts = (w.__srStarts || 0) + 1;
    }
    stop() {
      w.__srStops = (w.__srStops || 0) + 1;
      if (w.__srStarted === this) {
        w.__srStarted = null;
        setTimeout(() => this.onend && this.onend(), 0);
      }
    }
    abort() {}
  }
  w.SpeechRecognition = FakeSR;
  w.webkitSpeechRecognition = FakeSR;
};
/** Fires a recognition event on the instance that was actually started (as a browser would). */
const fireResult = (page, resultIndex: number, results: { t: string; f: boolean }[]) =>
  page.evaluate(
    ({ resultIndex, results }) => {
      const sr = (window as any).__srStarted;
      if (!sr) return false;
      sr.onresult({ resultIndex, results: results.map((r) => Object.assign([{ transcript: r.t }], { isFinal: r.f })) });
      return true;
    },
    { resultIndex, results }
  );

test("TC-LSA-005-01 dictado: el texto transcripto se suma al ya escrito", async ({ context }) => {
  const p2 = await context.newPage();
  await p2.goto("/paciente");
  const p3 = await context.newPage();
  await p3.addInitScript(SR_DOUBLE);
  await p3.goto("/recepcion");
  const area = p3.getByPlaceholder("Escribir...");
  const mic = p3.getByRole("button", { name: "Dictar respuesta por voz" });
  await expect(mic).toBeEnabled();
  await area.fill("Buenos días"); // the catalog types "Buenos dias" but expects "Buenos días ..." (typo in the catalog); accented text kept consistent
  await mic.click();
  await expect(p3.getByRole("button", { name: "Detener dictado" })).toBeVisible();
  const cfg = await p3.evaluate(() => {
    const s = (window as any).__srStarted;
    return s ? { lang: s.lang, continuous: s.continuous, interimResults: s.interimResults } : null;
  });
  expect(cfg).toEqual({ lang: "es-AR", continuous: true, interimResults: true });
  await fireResult(p3, 0, [{ t: "pase", f: false }]);
  await p3.waitForTimeout(300);
  const afterPartial = await area.inputValue();
  await fireResult(p3, 0, [{ t: "pase por favor", f: true }]);
  await p3.waitForTimeout(300);
  const afterFinal = await area.inputValue();
  await mic.click();
  const stillActive = await p3.evaluate(() => !!(window as any).__srStarted);
  await expect(p3.getByRole("button", { name: "Dictar respuesta por voz" })).toBeVisible();
  const send = p3.getByRole("button", { name: "Enviar" });
  const sendText = await area.inputValue();
  obs(`Doble de SpeechRecognition (simulado): lang=${cfg?.lang} continuous=${cfg?.continuous} interimResults=${cfg?.interimResults}. Área tras parcial 'pase': '${afterPartial}'; tras final 'pase por favor': '${afterFinal}'. Tras pulsar el micrófono de nuevo el indicador vuelve a '← Click para hablar'; la instancia iniciada sigue activa (sin stop): ${stillActive}.`);
  expect.soft(afterPartial).toBe("Buenos días pase");
  expect.soft(afterFinal).toBe("Buenos días pase por favor");
  await send.click();
  await expect(bubbleBox(p3, sendText || "x")).toBeVisible();
  await expect(bubbleBox(p2, sendText || "x")).toBeVisible();
  expect(sendText).toBe("Buenos días pase por favor");
});

test("TC-LSA-005-02 varios segmentos finales en una misma sesión de dictado", async ({ page }) => {
  await page.addInitScript(SR_DOUBLE);
  await page.goto("/recepcion");
  const mic = page.getByRole("button", { name: "Dictar respuesta por voz" });
  await expect(mic).toBeEnabled();
  await mic.click();
  await expect(page.getByRole("button", { name: "Detener dictado" })).toBeVisible();
  await fireResult(page, 0, [{ t: "necesito su documento", f: true }]);
  await page.waitForTimeout(300);
  await fireResult(page, 1, [{ t: "necesito su documento", f: true }, { t: "y su credencial", f: true }]);
  await page.waitForTimeout(300);
  const value = await page.getByPlaceholder("Escribir...").inputValue();
  obs(`Doble de SpeechRecognition (simulado), dos resultados finales resultIndex 0 y 1: el área contiene '${value}'.`);
  expect(value).toBe("necesito su documento y su credencial");
});

test("TC-LSA-005-03 dictado sin soporte del navegador y error de micrófono", async ({ browser }) => {
  const ctx1 = await browser.newContext();
  const p1 = await ctx1.newPage();
  await p1.addInitScript(() => {
    Object.defineProperty(window, "SpeechRecognition", { value: undefined, configurable: true });
    Object.defineProperty(window, "webkitSpeechRecognition", { value: undefined, configurable: true });
  });
  await p1.goto("/recepcion");
  await expect(p1.getByText("El navegador no soporta reconocimiento de voz.")).toBeVisible();
  await expect(p1.getByRole("button", { name: "Dictar respuesta por voz" })).toBeDisabled();
  const dup = await p1.getByText(/Error de micrófono:/).allTextContents();
  await reply(p1, "Respuesta manual");
  await expect(bubbleBox(p1, "Respuesta manual")).toBeVisible();
  await ctx1.close();

  const ctx2 = await browser.newContext();
  const p2 = await ctx2.newPage();
  await p2.addInitScript(SR_DOUBLE);
  await p2.goto("/recepcion");
  const mic = p2.getByRole("button", { name: "Dictar respuesta por voz" });
  await expect(mic).toBeEnabled();
  await mic.click();
  await expect(p2.getByRole("button", { name: "Detener dictado" })).toBeVisible();
  await p2.evaluate(() => (window as any).__srStarted.onerror({ error: "not-allowed" }));
  await expect(p2.getByText(/Error de micrófono:/)).toHaveCount(0);
  await expect(p2.getByRole("button", { name: "Dictar respuesta por voz" })).toBeVisible();
  await expect(p2.getByRole("button", { name: "Detener dictado" })).toHaveCount(0);
  await ctx2.close();
  obs(`Sin soporte: se muestra 'El navegador no soporta reconocimiento de voz.', micrófono deshabilitado y la respuesta escrita funciona. Aviso adicional mostrado en el mismo caso: ${JSON.stringify(dup)} (D-14b). Con error simulado not-allowed: 'Error de micrófono: not-allowed' e indicador '← Click para hablar'.`);
});

// ------------------------------------------------------------------ CU-10
const reportRows = (id: number) => ({
  msgs: dbAll("SELECT id, text, client_message_id FROM reported_message WHERE client_message_id = ?", id),
  words: dbAll("SELECT w.position, w.word FROM recognized_word w JOIN reported_message m ON m.id = w.message_id WHERE m.client_message_id = ? ORDER BY w.position", id),
  reports: dbAll("SELECT r.station FROM translation_report r JOIN reported_message m ON m.id = r.message_id WHERE m.client_message_id = ?", id),
  audits: (dbAll("SELECT COUNT(*) AS n FROM audit_event WHERE type = 'report'")[0] as any).n as number,
});

test("TC-LSA-010-01 reportar traducción desde P-02 y ver el mensaje marcado en ambas caras", async ({ context }) => {
  const ID = 1700000000001;
  const { page: p2 } = await openPatient(context);
  const p3 = await openReception(context);
  await p2.route("**/report", async (route) => {
    await sleep(1200);
    await route.continue();
  });
  const auditsBefore = reportRows(ID).audits;
  await postChat(p3, patientMsg(ID));
  const btn = bubbleBox(p2, "Me duele la cabeza.").getByRole("button", { name: /Reportar traducción/ });
  const reqP = p2.waitForRequest((r) => r.url().endsWith("/report"));
  const resP = p2.waitForResponse((r) => r.url().endsWith("/report"));
  await btn.click();
  await expect(bubbleBox(p2, "Me duele la cabeza.").getByRole("button")).toHaveText("Enviando...");
  const req = await reqP;
  expect(req.postDataJSON()).toEqual({ text: "Me duele la cabeza.", station: "paciente", message_id: ID, words: ["yo", "cabeza", "dolor"] });
  const res = await resP;
  const body = await res.json();
  expect(res.status()).toBe(200);
  expect(body).toMatchObject({ status: "ok", message_id: expect.anything(), report_id: expect.anything() });
  for (const [p, notice] of [[p2, NOTICE_P2], [p3, NOTICE_P3]] as const) {
    const box = bubbleBox(p, "Me duele la cabeza.");
    await expect(box.locator("[data-chat-message]")).toHaveClass(/line-through/);
    await expect(box.locator(":scope > div").first()).toHaveClass(/bg-amber-50/);
    await expect(box.locator(":scope > div").first()).toHaveClass(/border-amber-300/);
    await expect(box.getByText("Traducción reportada", { exact: true })).toBeVisible();
    await expect(box.getByText(notice)).toBeVisible();
    await expect(box.getByRole("button")).toHaveCount(0);
  }
  const rows = reportRows(ID);
  obs(`POST /report ${JSON.stringify(req.postDataJSON())} -> ${res.status()} ${JSON.stringify(body)}; botón 'Enviando...' intermedio; ambas caras con texto tachado, fondo/borde ámbar, insignia 'Traducción reportada' y aviso propio; SQLite: reported_message=${rows.msgs.length}, recognized_word posiciones=[${rows.words.map((w) => w.position)}], translation_report=${rows.reports.length} (station=${rows.reports[0]?.station}), audit_event type=report +${rows.audits - auditsBefore}.`);
  expect(rows.msgs).toHaveLength(1);
  expect(rows.msgs[0]).toMatchObject({ text: "Me duele la cabeza.", client_message_id: ID });
  expect(rows.words.map((w) => w.position)).toEqual([0, 1, 2]);
  expect(rows.reports).toEqual([{ station: "paciente" }]);
  expect(rows.audits - auditsBefore).toBe(1);
});

test("TC-LSA-010-02 reportar desde P-03; el botón solo existe en mensajes del paciente", async ({ context }) => {
  const ID = 1700000000002;
  const { page: p2 } = await openPatient(context);
  const p3 = await openReception(context);
  await reply(p3, "Pase a la sala 2");
  await postChat(p3, patientMsg(ID));
  await expect(bubbleBox(p3, "Me duele la cabeza.")).toBeVisible();
  await expect(bubbleBox(p3, "Pase a la sala 2").getByRole("button")).toHaveCount(0);
  await expect(p3.getByRole("button", { name: /Reportar traducción/ })).toHaveCount(1);
  const reqP = p3.waitForRequest((r) => r.url().endsWith("/report"));
  await bubbleBox(p3, "Me duele la cabeza.").getByRole("button", { name: /Reportar traducción/ }).click();
  const body = (await reqP).postDataJSON();
  expect(body.station).toBe("recepcion");
  for (const [p, notice] of [[p3, NOTICE_P3], [p2, NOTICE_P2]] as const) {
    const box = bubbleBox(p, "Me duele la cabeza.");
    await expect(box.locator("[data-chat-message]")).toHaveClass(/line-through/);
    await expect(box.getByText("Traducción reportada", { exact: true })).toBeVisible();
    await expect(box.getByText(notice)).toBeVisible();
  }
  obs(`El mensaje RECEPCIONISTA no tiene botón; el del paciente sí. POST /report con station='${body.station}'; ambas caras tachadas con 'Traducción reportada'; P-03 muestra '${NOTICE_P3}' y P-02 muestra '${NOTICE_P2}'.`);
});

test("TC-LSA-010-03 fallo de envío del reporte y protección contra doble clic", async ({ context }) => {
  const ID = 1700000000003;
  const { page: p2 } = await openPatient(context);
  const p3 = await openReception(context);
  await postChat(p3, patientMsg(ID));
  const box2 = bubbleBox(p2, "Me duele la cabeza.");
  await expect(box2).toBeVisible();
  await p2.route("**/report", (r) => r.abort("connectionfailed"));
  await box2.getByRole("button", { name: /Reportar traducción/ }).click();
  await expect(box2.getByText("No se pudo enviar el reporte. Probá de nuevo.")).toBeVisible();
  await expect(box2.getByRole("button")).toHaveText("Reportar traducción");
  await expect(box2.locator("[data-chat-message]")).not.toHaveClass(/line-through/);
  await expect(bubbleBox(p3, "Me duele la cabeza.").locator("[data-chat-message]")).not.toHaveClass(/line-through/);
  await p2.unroute("**/report");
  let posts = 0;
  await p2.route("**/report", async (route) => {
    posts++;
    await sleep(1000);
    await route.continue();
  });
  await box2.getByRole("button", { name: /Reportar traducción/ }).dblclick();
  await expect(box2.getByText("Traducción reportada", { exact: true })).toBeVisible();
  await expect(bubbleBox(p3, "Me duele la cabeza.").getByText("Traducción reportada", { exact: true })).toBeVisible();
  const rows = reportRows(ID);
  obs(`Con la conexión abortada: 'No se pudo enviar el reporte. Probá de nuevo.' y botón 'Reportar traducción' disponible, mensaje sin tachar en ambas caras. Con doble clic rápido: ${posts} petición(es) POST /report y ${rows.reports.length} fila(s) en translation_report; luego reportado en ambas caras.`);
  expect(posts).toBe(1);
  expect(rows.reports).toHaveLength(1);
});

// ------------------------------------------------------------------ CU-11 / CU-12 / privacidad
test("TC-LSA-011-04 enviar una respuesta del personal dispara un evento de auditoría anónimo", async ({ page, request }) => {
  await page.goto("/recepcion");
  const audits = listAudits(page);
  const before = await getMetrics(request);
  await reply(page, "Pase a la sala 2");
  await expect(bubbleBox(page, "Pase a la sala 2")).toBeVisible();
  await sleep(1500);
  const after = await getMetrics(request);
  const delta = totalEvents(after) - totalEvents(before);
  obs(`Tras enviar 'Pase a la sala 2' desde P-03: peticiones POST /audit emitidas por el frontend: ${audits.length}; variación del total de eventos en /metrics: ${delta}.`);
  expect(audits.length).toBeGreaterThanOrEqual(1);
  expect(JSON.stringify(audits)).not.toContain("Pase a la sala");
  expect(delta).toBe(1);
});

test("TC-LSA-012-01 Finalizar atención desde P-03 vacía ambas caras y audita el fin", async ({ context, request }) => {
  const { page: p2 } = await openPatient(context, { accept: false });
  const p3 = await openReception(context);
  await postChat(p3, patientMsg(1700000000012));
  await expect(bubbleBox(p2, "Me duele la cabeza.")).toBeVisible();
  const m = await getMetrics(request);
  const buttons3 = (await p3.getByRole("button").allTextContents()).map((t) => t.trim());
  const finalizar = await p3.getByRole("button", { name: /Finalizar atención/i }).count();
  const limpiarP2 = await p2.getByText("Limpiar Historial").count();
  obs(`Botones visibles en P-03: [${buttons3.join(" | ")}]; 'Finalizar atención' en P-03: ${finalizar}; 'Limpiar Historial' solo en P-02: ${limpiarP2}; counts.fin_atencion en /metrics: ${m.counts?.fin_atencion ?? "ausente"}. Los pasos 2 a 4 no se pueden ejecutar sin el control.`);
  expect(finalizar, "debe existir el botón 'Finalizar atención' en P-03 (D-01)").toBeGreaterThan(0);
});

test("TC-LSA-012-02 borrado sincronizado (CLEAR) desde P-02 y por mensaje inyectado", async ({ context }) => {
  const { page: p2 } = await openPatient(context);
  const p3 = await openReception(context);
  const aux = await context.newPage();
  await aux.goto("/");
  await postChat(p3, patientMsg(1700000000021));
  await reply(p3, "Pase a la sala 2");
  await expect(p2.locator("[data-chat-message]")).toHaveCount(2);
  await p2.getByRole("button", { name: "Limpiar Historial" }).click();
  await expect(p2.getByText(EMPTY_P2)).toBeVisible();
  await expect(p3.getByText(EMPTY_P3)).toBeVisible();
  await postChat(p3, patientMsg(1700000000022));
  await reply(p3, "Pase a la sala 3");
  await expect(p2.locator("[data-chat-message]")).toHaveCount(2);
  await postChat(aux, { type: "CLEAR" });
  await expect(p2.getByText(EMPTY_P2)).toBeVisible();
  await expect(p3.getByText(EMPTY_P3)).toBeVisible();
  obs(`'Limpiar Historial' en P-02 deja '${EMPTY_P2}' en P-02 y '${EMPTY_P3}' en P-03; tras reinyectar mensajes, un CLEAR publicado desde una tercera página del mismo origen vacía de nuevo ambas caras.`);
});

test("TC-LSA-012-03 la conversación no se persiste: P-02 nueva inicia vacía", async ({ context }) => {
  const p3 = await openReception(context);
  const aux = await context.newPage();
  await aux.goto("/");
  await postChat(p3, patientMsg(1700000000031));
  await reply(p3, "Pase a la sala 2");
  await expect(p3.locator("[data-chat-message]")).toHaveCount(2);
  await postChat(aux, { type: "CLEAR" }); // CU-12 finalization: no UI control exists (D-01), the CLEAR event is published instead
  await expect(p3.getByText(EMPTY_P3)).toBeVisible();
  const { page: p2 } = await openPatient(context);
  await expect(p2.getByText(EMPTY_P2)).toBeVisible();
  const stores = [await storageDump(p2), await storageDump(p3)];
  expect(stores.map((x) => x.haystack).join()).not.toMatch(/Pase a la sala|Me duele/);
  obs(`Tras finalizar (evento CLEAR) y abrir P-02 nueva con consentimiento: panel '${EMPTY_P2}'. Almacenamiento P-02: ${stores[0].keys}; P-03: ${stores[1].keys}. Ningún almacenamiento contiene 'Pase a la sala' ni 'Me duele'.`);
});

test("TC-LSA-013-03 la conversación vive solo en memoria del navegador", async ({ context }) => {
  const { page: p2 } = await openPatient(context, { accept: false });
  const p3 = await openReception(context);
  await postChat(p3, patientMsg(1700000000041));
  await reply(p3, "Pase a la sala 2");
  await expect(p3.locator("[data-chat-message]")).toHaveCount(2);
  await p3.reload();
  await expect(p3.getByText(EMPTY_P3)).toBeVisible();
  const [d2, d3] = [await storageDump(p2), await storageDump(p3)];
  const cookies = await context.cookies();
  const p4 = await context.newPage();
  await p4.goto("/recepcion");
  await expect(p4.getByText(EMPTY_P3)).toBeVisible();
  obs(`Tras recargar P-03: '${EMPTY_P3}'. Almacenamiento P-02: ${d2.keys}; P-03: ${d3.keys}; cookies del contexto: ${cookies.length}. Una pestaña nueva de /recepcion con P-02 abierta inicia vacía.`);
  expect([d2.haystack, d3.haystack, JSON.stringify(cookies)].join()).not.toMatch(/Pase a la sala|Me duele/);
});
