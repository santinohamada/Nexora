import { useEffect, useRef, useState, useCallback } from "react";
import { Status, Frame, Landmark } from "../types";

declare global {
  interface Window {
    HolisticLandmarker?: any;
    PoseLandmarker?: any;
    HandLandmarker?: any;
    FilesetResolver?: any;
    __mediapipeBench?: {
      fps: number;
      inferenceMs: number;
      framesProcessed: number;
      droppedFrames: number;
    };
  }
}

type UseMediaPipeTasksOptions = {
  onFrame?: (frame: Frame) => void;
  drawLandmarksOnCanvas?: boolean;
};

const MEDIAPIPE_TASKS_VERSION = "0.10.14";
const MEDIAPIPE_TASKS_CDN = `https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@${MEDIAPIPE_TASKS_VERSION}`;
const MEDIAPIPE_TASKS_WASM = `${MEDIAPIPE_TASKS_CDN}/wasm`;
const MEDIAPIPE_STRIDE = 2;
const HOLISTIC_MODEL_URL =
  "https://storage.googleapis.com/mediapipe-models/holistic_landmarker/holistic_landmarker/float16/latest/holistic_landmarker.task";
const POSE_MODEL_URL =
  "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task";
const HAND_MODEL_URL =
  "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task";
const FPS_WINDOW = 60;

function loadTasksVisionBundle(): Promise<void> {
  return new Promise((resolve, reject) => {
    if (
      typeof window !== "undefined" &&
      (window.HolisticLandmarker || window.PoseLandmarker) &&
      window.FilesetResolver
    ) {
      resolve();
      return;
    }
    if (typeof document === "undefined") {
      reject(new Error("document unavailable"));
      return;
    }
    const existing = document.querySelector(
      `script[data-mp-tasks-vision-bundle]`
    );
    if (existing) {
      existing.addEventListener("load", () => resolve());
      existing.addEventListener("error", () =>
        reject(new Error("MediaPipe Tasks bundle failed to load"))
      );
      return;
    }
    const script = document.createElement("script");
    script.src = `${MEDIAPIPE_TASKS_CDN}/vision_bundle.mjs`;
    script.type = "module";
    script.dataset.mpTasksVisionBundle = "true";
    script.onload = () => resolve();
    script.onerror = () =>
      reject(new Error("MediaPipe Tasks bundle failed to load"));
    document.head.appendChild(script);
  });
}

function padLandmarks(
  lms: { x: number; y: number; z: number; visibility?: number }[] | undefined,
  n: number,
  defaultVis = 0
): Landmark[] {
  if (!lms || lms.length === 0) {
    return Array.from({ length: n }, () => [0, 0, 0, defaultVis]) as Landmark[];
  }
  return lms
    .slice(0, n)
    .map(
      (lm) =>
        [lm.x, lm.y, lm.z, lm.visibility ?? defaultVis] as Landmark
    );
}

function normalizeToNose(frame: Landmark[]): Landmark[] {
  const nose = frame[0];
  if (!nose) return frame;
  return frame.map(
    (lm) => [lm[0] - nose[0], lm[1] - nose[1], lm[2], lm[3]] as Landmark
  );
}

type LandmarkerBundle =
  | { kind: "holistic"; landmarker: any }
  | { kind: "split"; pose: any; left: any; right: any };

async function createLandmarkers(): Promise<LandmarkerBundle> {
  const { HolisticLandmarker, PoseLandmarker, HandLandmarker, FilesetResolver } =
    window;
  if (!FilesetResolver) {
    throw new Error("FilesetResolver missing");
  }
  const vision = await FilesetResolver.forVisionTasks(
    MEDIAPIPE_TASKS_WASM
  );
  if (HolisticLandmarker && typeof HolisticLandmarker.createFromOptions === "function") {
    try {
      const landmarker = await HolisticLandmarker.createFromOptions(vision, {
        baseOptions: { modelAssetPath: HOLISTIC_MODEL_URL },
        runningMode: "VIDEO",
      });
      return { kind: "holistic", landmarker };
    } catch (e) {
      console.warn("[Nexora] HolisticLandmarker init failed, falling back", e);
    }
  }
  if (
    PoseLandmarker &&
    HandLandmarker &&
    typeof PoseLandmarker.createFromOptions === "function" &&
    typeof HandLandmarker.createFromOptions === "function"
  ) {
    const [pose, left, right] = await Promise.all([
      PoseLandmarker.createFromOptions(vision, {
        baseOptions: { modelAssetPath: POSE_MODEL_URL },
        runningMode: "VIDEO",
        numPoses: 1,
      }),
      HandLandmarker.createFromOptions(vision, {
        baseOptions: { modelAssetPath: HAND_MODEL_URL },
        runningMode: "VIDEO",
        numHands: 2,
      }),
      HandLandmarker.createFromOptions(vision, {
        baseOptions: { modelAssetPath: HAND_MODEL_URL },
        runningMode: "VIDEO",
        numHands: 2,
      }),
    ]);
    return { kind: "split", pose, left, right };
  }
  throw new Error("MediaPipe Tasks: no usable landmarker");
}

function extractFrameFromBundle(
  bundle: LandmarkerBundle,
  result: any,
  video: HTMLVideoElement
): Landmark[] {
  if (bundle.kind === "holistic") {
    const poseLandmarks = result?.poseLandmarks?.[0];
    const leftHand = result?.leftHandLandmarks?.[0];
    const rightHand = result?.rightHandLandmarks?.[0];
    return normalizeToNose([
      ...padLandmarks(poseLandmarks, 33),
      ...padLandmarks(leftHand, 21),
      ...padLandmarks(rightHand, 21),
    ]);
  }
  const poseLandmarks = result?.poseLandmarks?.[0]
    ?? result?.landmarks?.[0]
    ?? result;
  const leftHand = result?.leftHandLandmarks?.[0]
    ?? result?.handLandmarks?.[0];
  const rightHand = result?.rightHandLandmarks?.[0]
    ?? result?.handLandmarks?.[1];
  return normalizeToNose([
    ...padLandmarks(poseLandmarks, 33),
    ...padLandmarks(leftHand, 21),
    ...padLandmarks(rightHand, 21),
  ]);
}

export function useMediaPipeTasks({ onFrame }: UseMediaPipeTasksOptions = {}) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const onFrameRef = useRef(onFrame);
  const landmarkersRef = useRef<LandmarkerBundle | null>(null);
  const isSendingRef = useRef(false);
  const streamRef = useRef<MediaStream | null>(null);
  const frameIndexRef = useRef(0);
  const fpsWindowRef = useRef<number[]>([]);
  const inferenceMsWindowRef = useRef<number[]>([]);
  const framesProcessedRef = useRef(0);
  const droppedFramesRef = useRef(0);
  const [status, setStatus] = useState<Status>("loading");
  const [error, setError] = useState<string | null>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const lastBenchmarkRef = useRef<{
    fps: number;
    inferenceMs: number;
  } | null>(null);

  const setVideoNode = useCallback((node: HTMLVideoElement | null) => {
    videoRef.current = node;
    if (node && streamRef.current && node.srcObject !== streamRef.current) {
      node.srcObject = streamRef.current;
      node.play().catch(() => {});
    }
  }, []);

  useEffect(() => {
    onFrameRef.current = onFrame;
  }, [onFrame]);

  useEffect(() => {
    let isMounted = true;
    let warned = false;
    loadTasksVisionBundle()
      .then(() => createLandmarkers())
      .then((bundle) => {
        if (!isMounted) return;
        landmarkersRef.current = bundle;
        setStatus("idle");
      })
      .catch((err) => {
        if (warned) return;
        warned = true;
        console.warn(
          "[Nexora] MediaPipe Tasks harness failed to load; benchmark disabled.",
          err
        );
        if (isMounted) {
          setError("MediaPipe Tasks unavailable");
          setStatus("error");
        }
      });
    return () => {
      isMounted = false;
      const bundle = landmarkersRef.current;
      if (!bundle) return;
      try {
        if (bundle.kind === "holistic") {
          bundle.landmarker.close?.();
        } else {
          bundle.pose.close?.();
          bundle.left.close?.();
          bundle.right.close?.();
        }
      } catch (e) {
        /* landmarker may already be closed */
      }
    };
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const id = window.setInterval(() => {
      const fps = lastBenchmarkRef.current?.fps ?? 0;
      const inferenceMs = lastBenchmarkRef.current?.inferenceMs ?? 0;
      window.__mediapipeBench = {
        fps,
        inferenceMs,
        framesProcessed: framesProcessedRef.current,
        droppedFrames: droppedFramesRef.current,
      };
    }, 500);
    return () => window.clearInterval(id);
  }, []);

  useEffect(() => {
    if (typeof navigator === "undefined") return;
    let cancelled = false;
    navigator.mediaDevices
      .getUserMedia({
        video: { width: { ideal: 1280 }, height: { ideal: 720 }, frameRate: { ideal: 30 } },
      })
      .then((s) => {
        if (cancelled) return;
        streamRef.current = s;
        setStream(s);
        if (videoRef.current) {
          videoRef.current.srcObject = s;
          videoRef.current.onloadedmetadata = () => {
            videoRef.current?.play().catch(() => {});
          };
        }
      })
      .catch(() => {
        if (cancelled) return;
        setError("No se pudo acceder a la cámara.");
        setStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    const startLoop = () => {
      const loop = () => {
        if (cancelled) return;
        const bundle = landmarkersRef.current;
        const video = videoRef.current;
        if (
          bundle &&
          video &&
          video.readyState >= 2 &&
          !isSendingRef.current
        ) {
          if (frameIndexRef.current++ % MEDIAPIPE_STRIDE === 0) {
            isSendingRef.current = true;
            const sendTs = performance.now();
            try {
              let result: any;
              if (bundle.kind === "holistic") {
                result = bundle.landmarker.detectForVideo(video, sendTs);
              } else {
                const [poseRes, handRes] = [
                  bundle.pose.detectForVideo(video, sendTs),
                  bundle.left.detectForVideo(video, sendTs),
                ];
                const rightRes = bundle.right.detectForVideo(video, sendTs);
                result = {
                  poseLandmarks: poseRes?.landmarks,
                  leftHandLandmarks: handRes?.handLandmarks,
                  handLandmarks: handRes?.handLandmarks,
                  rightHandLandmarks: rightRes?.handLandmarks,
                };
              }
              const inferenceMs = performance.now() - sendTs;
              inferenceMsWindowRef.current.push(inferenceMs);
              if (inferenceMsWindowRef.current.length > FPS_WINDOW) {
                inferenceMsWindowRef.current.shift();
              }
              fpsWindowRef.current.push(performance.now());
              if (fpsWindowRef.current.length > FPS_WINDOW) {
                fpsWindowRef.current.shift();
              }
              let sum = 0;
              for (const x of inferenceMsWindowRef.current) sum += x;
              const avgInf = inferenceMsWindowRef.current.length > 0
                ? sum / inferenceMsWindowRef.current.length
                : 0;
              const wins = fpsWindowRef.current;
              let intervalSum = 0;
              for (let i = 1; i < wins.length; i++) {
                intervalSum += wins[i] - wins[i - 1];
              }
              const avgInterval = wins.length > 1
                ? intervalSum / (wins.length - 1)
                : 0;
              const fps = avgInterval > 0 ? 1000 / avgInterval : 0;
              lastBenchmarkRef.current = {
                fps: Math.round(fps * 100) / 100,
                inferenceMs: Math.round(avgInf * 100) / 100,
              };
              framesProcessedRef.current++;
              const frame = extractFrameFromBundle(bundle, result, video);
              onFrameRef.current?.(frame);
            } catch (e) {
              droppedFramesRef.current++;
            } finally {
              isSendingRef.current = false;
            }
          }
        }
        requestAnimationFrame(loop);
      };
      requestAnimationFrame(loop);
    };
    startLoop();
    return () => {
      cancelled = true;
    };
  }, []);

  return { videoRef: setVideoNode, canvasRef, status, setStatus, error, stream };
}
