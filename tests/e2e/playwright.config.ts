import { defineConfig } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";

const root = path.resolve(__dirname, "..", "..");
const tmp = path.join(__dirname, ".tmp");
fs.mkdirSync(tmp, { recursive: true });
const testDb = path.join(tmp, "test.db");
const python = process.env.PYTHON ?? path.join(root, "venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
// Fresh DB each run, never data/lsa_salud.db. Only in the main process: workers re-import this
// config and would delete the DB under the running backend.
if (!process.env.TEST_WORKER_INDEX) for (const f of ["test.db", "test.db-wal", "test.db-shm"]) fs.rmSync(path.join(tmp, f), { force: true });

// Isolated runtime tree: the backend resolves dataset/, models/ and voices/ relative to its cwd, so it runs from a
// copy and /capture never writes into the repo's dataset/. Built only in the main process (workers re-import this config).
const runtime = path.join(tmp, "runtime");
if (!process.env.TEST_WORKER_INDEX) {
  fs.rmSync(runtime, { recursive: true, force: true });
  fs.mkdirSync(runtime, { recursive: true });
  for (const f of ["app.py", "storage.py", "capture_validation.py"]) fs.copyFileSync(path.join(root, f), path.join(runtime, f));
  for (const d of ["src", "models", "dataset"]) fs.cpSync(path.join(root, d), path.join(runtime, d), { recursive: true });
  if (fs.existsSync(path.join(root, "voices"))) fs.symlinkSync(path.join(root, "voices"), path.join(runtime, "voices"), "junction"); // read-only voice model
  else console.warn("[tests] voices/ not found: the backend runs without Piper (no audio).");
}

export default defineConfig({
  testDir: "./specs",
  workers: 1,
  timeout: 60_000,
  expect: { timeout: 30_000 }, // MediaPipe in software rendering makes the page slow; positive assertions wait for it
  reporter: [["list"], ["json", { outputFile: "results/ui-results.json" }]],
  use: {
    baseURL: "http://localhost:3000",
    permissions: ["camera", "microphone"],
    launchOptions: {
      args: ["--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream"],
    },
  },
  projects: [{ name: "chromium", use: { browserName: "chromium" } }],
  webServer: [
    {
      // Fails fast if :8000 is taken, so a real backend (real DB) is never reused.
      command: `"${python}" -m uvicorn app:app --port 8000`,
      cwd: runtime,
      url: "http://localhost:8000/metrics",
      env: { NEXORA_DB_PATH: testDb },
      reuseExistingServer: false,
      timeout: 180_000,
    },
    {
      command: "npm run dev",
      cwd: path.join(root, "web"),
      url: "http://localhost:3000",
      env: { NEXT_PUBLIC_API_URL: "http://localhost:8000", NEXT_PUBLIC_MIN_SAMPLE_FPS: "0" },
      reuseExistingServer: true,
      timeout: 180_000,
    },
  ],
});
