import { useEffect, useRef, useState, useCallback } from "react";
import type { NormalizedLandmark } from "@mediapipe/tasks-vision";
import { Status, Frame } from "../types";
import {
  toFrame,
  resolveHandSlots,
  extractBlendshapes,
  isFaceEligibleTick,
  createLandmarkers,
  MediaPipeLandmarkerSet,
  TasksVisionModule,
} from "../lib/mediapipe";

declare global {
  interface Window {
    __mediapipeBench?: {
      fps: number;
      inferenceMs: number;
      framesProcessed: number;
      droppedFrames: number;
    };
  }
}

type UseMediaPipeTasksOptions = {
  onFrame?: (frame: Frame, blendshapes?: number[]) => void;
  drawLandmarksOnCanvas?: boolean;
  enabled?: boolean;
};

// Fixed sampling rate for capture and inference alike, so a 45-frame window spans the same time on
// every machine. Slower machines (CPU fallback) just run below it.
const TARGET_FPS = 20;
const TARGET_INTERVAL_MS = 1000 / TARGET_FPS;
const FPS_WINDOW = 60;
const CAPTURE_WIDTH = 640;
const CAPTURE_HEIGHT = 360;

export function useMediaPipeTasks({
  onFrame,
  drawLandmarksOnCanvas = true,
  enabled = true,
}: UseMediaPipeTasksOptions = {}) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const onFrameRef = useRef(onFrame);
  const landmarkersRef = useRef<MediaPipeLandmarkerSet | null>(null);
  const visionRef = useRef<TasksVisionModule | null>(null);
  const drawLandmarksRef = useRef(drawLandmarksOnCanvas);
  // Detectors get a downscaled canvas copy of the frame: passing the live <video> element directly
  // made every detector return empty results.
  const inputCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const isSendingRef = useRef(false);
  const streamRef = useRef<MediaStream | null>(null);
  const nextTickRef = useRef(0);
  const eligibleTickRef = useRef(0);
  const latestBlendshapesRef = useRef<number[]>(new Array(52).fill(0));
  const fpsWindowRef = useRef<number[]>([]);
  const inferenceMsWindowRef = useRef<number[]>([]);
  const framesProcessedRef = useRef(0);
  const droppedFramesRef = useRef(0);
  const [status, setStatus] = useState<Status>("loading");
  const [error, setError] = useState<string | null>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const lastBenchmarkRef = useRef<{ fps: number; inferenceMs: number } | null>(null);

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
    drawLandmarksRef.current = drawLandmarksOnCanvas;
  }, [drawLandmarksOnCanvas]);

  useEffect(() => {
    let isMounted = true;
    import("@mediapipe/tasks-vision")
      .then((visionModule) => {
        visionRef.current = visionModule;
        return createLandmarkers(visionModule);
      })
      .then((landmarkers) => {
        if (!isMounted) return;
        landmarkersRef.current = landmarkers;
        setStatus("idle");
      })
      .catch((err) => {
        console.warn("[Nexora] MediaPipe Tasks pipeline failed to load", err);
        if (isMounted) {
          setError("MediaPipe Tasks unavailable");
          setStatus("error");
        }
      });
    return () => {
      isMounted = false;
      const landmarkers = landmarkersRef.current;
      if (!landmarkers) return;
      try {
        landmarkers.pose.close();
        landmarkers.hand.close();
        landmarkers.face.close();
      } catch (e) {
        /* landmarker may already be closed */
      }
    };
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const id = window.setInterval(() => {
      window.__mediapipeBench = {
        fps: lastBenchmarkRef.current?.fps ?? 0,
        inferenceMs: lastBenchmarkRef.current?.inferenceMs ?? 0,
        framesProcessed: framesProcessedRef.current,
        droppedFrames: droppedFramesRef.current,
      };
    }, 500);
    return () => window.clearInterval(id);
  }, []);

  useEffect(() => {
    if (typeof navigator === "undefined") return;
    if (!enabled) return;
    let cancelled = false;
    navigator.mediaDevices
      .getUserMedia({
        video: {
          width: { ideal: CAPTURE_WIDTH },
          height: { ideal: CAPTURE_HEIGHT },
          frameRate: { ideal: 30 },
        },
      })
      .then((s) => {
        if (cancelled) {
          s.getTracks().forEach((t) => t.stop());
          return;
        }
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
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
        streamRef.current = null;
      }
    };
  }, [enabled]);

  const drawSkeleton = (
    pose: NormalizedLandmark[] | undefined,
    hands: NormalizedLandmark[][],
    width: number,
    height: number
  ) => {
    const canvas = canvasRef.current;
    const vision = visionRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !vision || !ctx) return;
    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width;
      canvas.height = height;
    }
    ctx.clearRect(0, 0, width, height);
    if (!drawLandmarksRef.current) return;
    const utils = new vision.DrawingUtils(ctx);
    if (pose) {
      utils.drawConnectors(pose, vision.PoseLandmarker.POSE_CONNECTIONS, { color: "#4f46e5", lineWidth: 2 });
      utils.drawLandmarks(pose, { color: "#818cf8", lineWidth: 1, radius: 2 });
    }
    for (const hand of hands) {
      utils.drawConnectors(hand, vision.HandLandmarker.HAND_CONNECTIONS, { color: "#10b981", lineWidth: 2 });
      utils.drawLandmarks(hand, { color: "#6ee7b7", lineWidth: 1, radius: 2 });
    }
  };

  useEffect(() => {
    let cancelled = false;
    const loop = () => {
      if (cancelled) return;
      const landmarkers = landmarkersRef.current;
      const video = videoRef.current;
      if (landmarkers && video && video.readyState >= 2 && !isSendingRef.current) {
        const now = performance.now();
        // -2 ms: rAF ticks jitter around the display period (60 Hz -> every 3rd tick at 50 ms)
        if (now >= nextTickRef.current - 2) {
          // Advance on a fixed schedule so a late tick doesn't push every following one; resync if far behind.
          nextTickRef.current =
            now - nextTickRef.current > TARGET_INTERVAL_MS ? now + TARGET_INTERVAL_MS : nextTickRef.current + TARGET_INTERVAL_MS;
          isSendingRef.current = true;
          eligibleTickRef.current++;
          const ts = performance.now();
          try {
            const input = (inputCanvasRef.current ??= document.createElement("canvas"));
            const w = CAPTURE_WIDTH;
            const h = Math.round((CAPTURE_WIDTH * video.videoHeight) / video.videoWidth);
            if (input.width !== w || input.height !== h) {
              input.width = w;
              input.height = h;
            }
            input.getContext("2d")!.drawImage(video, 0, 0, w, h);
            const poseResult = landmarkers.pose.detectForVideo(input, ts);
            const handResult = landmarkers.hand.detectForVideo(input, ts);
            const { left, right } = resolveHandSlots(
              poseResult.landmarks[0],
              handResult.landmarks,
              handResult.handedness
            );

            if (isFaceEligibleTick(eligibleTickRef.current)) {
              const faceResult = landmarkers.face.detectForVideo(input, ts);
              latestBlendshapesRef.current = extractBlendshapes(
                faceResult.faceBlendshapes?.[0]?.categories
              );
            }

            const inferenceMs = performance.now() - ts;
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
            const avgInf =
              inferenceMsWindowRef.current.length > 0
                ? sum / inferenceMsWindowRef.current.length
                : 0;
            const wins = fpsWindowRef.current;
            let intervalSum = 0;
            for (let i = 1; i < wins.length; i++) {
              intervalSum += wins[i] - wins[i - 1];
            }
            const avgInterval = wins.length > 1 ? intervalSum / (wins.length - 1) : 0;
            const fps = avgInterval > 0 ? 1000 / avgInterval : 0;
            lastBenchmarkRef.current = {
              fps: Math.round(fps * 100) / 100,
              inferenceMs: Math.round(avgInf * 100) / 100,
            };
            framesProcessedRef.current++;

            const frame = toFrame(poseResult.landmarks[0], left, right);
            onFrameRef.current?.(frame, latestBlendshapesRef.current);

            // After onFrame: a drawing failure must not drop the recorded frame
            drawSkeleton(poseResult.landmarks[0], handResult.landmarks, input.width, input.height);
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
    return () => {
      cancelled = true;
    };
  }, []);

  return { videoRef: setVideoNode, canvasRef, status, setStatus, error, stream };
}

export const MEDIAPIPE_TASKS_CAPTURE_SIZE = { width: CAPTURE_WIDTH, height: CAPTURE_HEIGHT };
