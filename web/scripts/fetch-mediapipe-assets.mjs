import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile, cp } from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const webRoot = path.resolve(__dirname, "..");
const modelsDir = path.join(webRoot, "public", "models");
const wasmDir = path.join(webRoot, "public", "mediapipe", "wasm");
const holisticDir = path.join(webRoot, "public", "mediapipe", "holistic");
const mediapipeModules = path.join(webRoot, "node_modules", "@mediapipe");
const wasmSourceDir = path.join(webRoot, "node_modules", "@mediapipe", "tasks-vision", "wasm");

const MODELS = [
  {
    name: "pose_landmarker_lite.task",
    url: "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task",
    sha256: "59929e1d1ee95287735ddd833b19cf4ac46d29bc7afddbbf6753c459690d574a",
  },
  {
    name: "hand_landmarker.task",
    url: "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task",
    sha256: "fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1",
  },
  {
    name: "face_landmarker.task",
    url: "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task",
    sha256: "64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff",
  },
];

async function sha256Of(filePath) {
  const buf = await readFile(filePath);
  return createHash("sha256").update(buf).digest("hex");
}

async function ensureModel(model) {
  const dest = path.join(modelsDir, model.name);
  if (existsSync(dest)) {
    const existingHash = await sha256Of(dest);
    if (existingHash === model.sha256) {
      console.log(`[fetch-mediapipe-assets] ${model.name} already present, hash OK`);
      return;
    }
    console.warn(`[fetch-mediapipe-assets] ${model.name} hash mismatch, re-downloading`);
  }
  console.log(`[fetch-mediapipe-assets] downloading ${model.name}`);
  const res = await fetch(model.url);
  if (!res.ok) {
    throw new Error(`[fetch-mediapipe-assets] failed to download ${model.url}: ${res.status}`);
  }
  const buf = Buffer.from(await res.arrayBuffer());
  const hash = createHash("sha256").update(buf).digest("hex");
  if (hash !== model.sha256) {
    throw new Error(
      `[fetch-mediapipe-assets] SHA-256 mismatch for ${model.name}: expected ${model.sha256}, got ${hash}`
    );
  }
  await writeFile(dest, buf);
  console.log(`[fetch-mediapipe-assets] ${model.name} verified and saved`);
}

async function ensureWasm() {
  if (!existsSync(wasmSourceDir)) {
    throw new Error(
      `[fetch-mediapipe-assets] ${wasmSourceDir} not found — run npm install first`
    );
  }
  await cp(wasmSourceDir, wasmDir, { recursive: true });
  console.log("[fetch-mediapipe-assets] wasm bundle copied to public/mediapipe/wasm");
}

// Legacy (default) landmark path: serve holistic + drawing_utils locally instead of cdn.jsdelivr.net (RNF-T-02).
async function ensureHolistic() {
  const holisticSrc = path.join(mediapipeModules, "holistic");
  const drawingSrc = path.join(mediapipeModules, "drawing_utils", "drawing_utils.js");
  if (!existsSync(holisticSrc) || !existsSync(drawingSrc)) {
    throw new Error("[fetch-mediapipe-assets] @mediapipe/holistic or drawing_utils not found — run npm install first");
  }
  await cp(holisticSrc, holisticDir, { recursive: true });
  await cp(drawingSrc, path.join(holisticDir, "drawing_utils.js"));
  console.log("[fetch-mediapipe-assets] holistic bundle copied to public/mediapipe/holistic");
}

async function main() {
  await mkdir(modelsDir, { recursive: true });
  await mkdir(wasmDir, { recursive: true });
  for (const model of MODELS) {
    await ensureModel(model);
  }
  await ensureWasm();
  await ensureHolistic();
}

main().catch((err) => {
  console.error(err.message || err);
  process.exit(1);
});
