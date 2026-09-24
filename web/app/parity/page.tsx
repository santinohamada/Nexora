"use client";

import { useRef, useState } from "react";
import { notFound } from "next/navigation";
import {
  toFrame,
  resolveHandSlots,
  loadScript,
  createLandmarkers,
  MediaPipeLandmarkerSet,
} from "../../lib/mediapipe";
import { Frame, PredictionResult } from "../../types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const REPLAY_FPS = 15;
const WARMUP_FRAMES = 20;
const PREDICT_STRIDE_FRAMES = 8;
const RECORDING_MAX_FRAMES = 45;
const HOLISTIC_SCRIPT_URL = "https://cdn.jsdelivr.net/npm/@mediapipe/holistic/holistic.js";
const OVERALL_AGREEMENT_THRESHOLD = 0.9;
const PER_CLASS_AGREEMENT_THRESHOLD = 0.8;
const MEAN_PROB_DIFF_THRESHOLD = 0.1;
const MIN_WINDOWS_PER_CLASS = 5;

type WindowResult = {
  legacy: PredictionResult;
  tasks: PredictionResult;
};

type ClassStat = {
  windows: number;
  agreement: number | "insufficient";
  meanProbDiff: number;
};

type ParityReport = {
  windows: number;
  overallAgreement: number;
  overallMeanProbDiff: number;
  perClass: Record<string, ClassStat>;
  pass: boolean;
};

declare global {
  interface Window {
    Holistic: any;
  }
}

function waitForSeeked(video: HTMLVideoElement, time: number): Promise<void> {
  return new Promise((resolve) => {
    const onSeeked = () => {
      video.removeEventListener("seeked", onSeeked);
      resolve();
    };
    video.addEventListener("seeked", onSeeked);
    video.currentTime = time;
  });
}

function detectLegacy(holistic: any, image: CanvasImageSource): Promise<any> {
  return new Promise((resolve) => {
    holistic.onResults((results: any) => resolve(results));
    holistic.send({ image });
  });
}

async function predict(frames: Frame[]): Promise<PredictionResult> {
  const res = await fetch(`${API_URL}/predict`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ frames }),
  });
  return res.json();
}

function pushCapped(buffer: Frame[], frame: Frame) {
  buffer.push(frame);
  if (buffer.length > RECORDING_MAX_FRAMES) buffer.shift();
}

function buildReport(results: WindowResult[]): ParityReport {
  const perClassWindows = new Map<string, WindowResult[]>();
  for (const r of results) {
    const c = r.legacy.sign;
    const arr = perClassWindows.get(c) ?? [];
    arr.push(r);
    perClassWindows.set(c, arr);
  }

  const perClass: Record<string, ClassStat> = {};
  for (const [c, windows] of perClassWindows) {
    const agree = windows.filter((w) => w.tasks.sign === c).length;
    const diffs = windows.map((w) => {
      const pTasks = w.tasks.top3.find((t) => t.sign === c)?.confidence ?? 0;
      const pLegacy = w.legacy.confidence;
      return Math.abs(pTasks - pLegacy) / 100;
    });
    perClass[c] = {
      windows: windows.length,
      agreement: windows.length >= MIN_WINDOWS_PER_CLASS ? agree / windows.length : "insufficient",
      meanProbDiff: diffs.reduce((a, b) => a + b, 0) / diffs.length,
    };
  }

  const overallAgreement =
    results.length > 0 ? results.filter((r) => r.tasks.sign === r.legacy.sign).length / results.length : 0;
  const overallDiffs = results.map((r) => {
    const c = r.legacy.sign;
    const pTasks = r.tasks.top3.find((t) => t.sign === c)?.confidence ?? 0;
    const pLegacy = r.legacy.confidence;
    return Math.abs(pTasks - pLegacy) / 100;
  });
  const overallMeanProbDiff =
    overallDiffs.length > 0 ? overallDiffs.reduce((a, b) => a + b, 0) / overallDiffs.length : 0;

  const perClassPass = Object.values(perClass).every(
    (s) => s.agreement === "insufficient" || s.agreement >= PER_CLASS_AGREEMENT_THRESHOLD
  );
  const pass =
    overallAgreement >= OVERALL_AGREEMENT_THRESHOLD &&
    overallMeanProbDiff <= MEAN_PROB_DIFF_THRESHOLD &&
    perClassPass;

  return { windows: results.length, overallAgreement, overallMeanProbDiff, perClass, pass };
}

export default function ParityPage() {
  if (process.env.NODE_ENV === "production") {
    notFound();
  }

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasARef = useRef<HTMLCanvasElement | null>(null);
  const canvasBRef = useRef<HTMLCanvasElement | null>(null);
  const [progress, setProgress] = useState("");
  const [running, setRunning] = useState(false);
  const [report, setReport] = useState<ParityReport | null>(null);

  const handleFile = async (file: File) => {
    setRunning(true);
    setReport(null);
    setProgress("loading video...");

    const video = videoRef.current;
    const canvasA = canvasARef.current;
    const canvasB = canvasBRef.current;
    if (!video || !canvasA || !canvasB) {
      setRunning(false);
      return;
    }

    video.src = URL.createObjectURL(file);
    await new Promise<void>((resolve) => {
      video.onloadedmetadata = () => resolve();
    });

    canvasA.width = video.videoWidth;
    canvasA.height = video.videoHeight;
    canvasB.width = 640;
    canvasB.height = 360;
    const ctxA = canvasA.getContext("2d")!;
    const ctxB = canvasB.getContext("2d")!;

    setProgress("loading legacy Holistic...");
    await loadScript(HOLISTIC_SCRIPT_URL);
    let attempts = 0;
    while (!window.Holistic && attempts < 40) {
      await new Promise((r) => setTimeout(r, 250));
      attempts++;
    }
    const holistic = new window.Holistic({
      locateFile: (f: string) => `https://cdn.jsdelivr.net/npm/@mediapipe/holistic/${f}`,
    });
    holistic.setOptions({
      modelComplexity: 0,
      smoothLandmarks: true,
      enableSegmentation: false,
      smoothSegmentation: false,
      refineFaceLandmarks: false,
      minDetectionConfidence: 0.5,
      minTrackingConfidence: 0.5,
    });

    setProgress("loading Tasks pipeline...");
    const visionModule = await import("@mediapipe/tasks-vision");
    const landmarkers: MediaPipeLandmarkerSet = await createLandmarkers(visionModule);

    const totalFrames = Math.floor(video.duration * REPLAY_FPS);
    const legacyBuffer: Frame[] = [];
    const tasksBuffer: Frame[] = [];
    const results: WindowResult[] = [];
    let framesSincePredict = 0;

    for (let k = 0; k < totalFrames; k++) {
      setProgress(`processing frame ${k + 1}/${totalFrames}`);
      await waitForSeeked(video, k / REPLAY_FPS);

      ctxA.drawImage(video, 0, 0, canvasA.width, canvasA.height);
      ctxB.drawImage(video, 0, 0, canvasB.width, canvasB.height);

      const legacyResults = await detectLegacy(holistic, canvasA);
      const legacyFrame = toFrame(
        legacyResults.poseLandmarks,
        legacyResults.leftHandLandmarks,
        legacyResults.rightHandLandmarks
      );
      pushCapped(legacyBuffer, legacyFrame);

      const ts = (k * 1000) / REPLAY_FPS;
      const poseResult = landmarkers.pose.detectForVideo(canvasB, ts);
      const handResult = landmarkers.hand.detectForVideo(canvasB, ts);
      const { left, right } = resolveHandSlots(handResult.landmarks, handResult.handedness);
      const tasksFrame = toFrame(poseResult.landmarks[0], left, right);
      pushCapped(tasksBuffer, tasksFrame);

      framesSincePredict++;
      if (legacyBuffer.length >= WARMUP_FRAMES && framesSincePredict >= PREDICT_STRIDE_FRAMES) {
        framesSincePredict = 0;
        const [legacyPred, tasksPred] = await Promise.all([
          predict([...legacyBuffer]),
          predict([...tasksBuffer]),
        ]);
        results.push({ legacy: legacyPred, tasks: tasksPred });
      }
    }

    try {
      holistic.close();
    } catch (e) {
      /* holistic may already be closed */
    }
    try {
      landmarkers.pose.close();
      landmarkers.hand.close();
      landmarkers.face.close();
    } catch (e) {
      /* landmarkers may already be closed */
    }

    setProgress(`done — ${results.length} windows`);
    setReport(buildReport(results));
    setRunning(false);
  };

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900 p-8">
      <h1 className="text-xl font-bold mb-4">MediaPipe Tasks parity harness (dev only)</h1>
      <input
        type="file"
        accept="video/*"
        disabled={running}
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) handleFile(file);
        }}
      />
      <p className="text-sm text-slate-600 mt-2">{progress}</p>
      <div className="flex gap-4 mt-4">
        <video ref={videoRef} className="hidden" muted playsInline />
        <canvas ref={canvasARef} className="border border-slate-300 max-w-[320px]" />
        <canvas ref={canvasBRef} className="border border-slate-300 max-w-[320px]" />
      </div>
      {report && (
        <div className="mt-6">
          <p className="font-semibold">{report.pass ? "PASS" : "FAIL"}</p>
          <pre className="bg-slate-900 text-slate-100 p-4 rounded-lg text-xs overflow-auto mt-2">
            {JSON.stringify(report, null, 2)}
          </pre>
        </div>
      )}
    </main>
  );
}
