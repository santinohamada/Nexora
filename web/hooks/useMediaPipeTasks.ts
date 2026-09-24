import { useEffect, useRef, useState, useCallback } from "react";
import { Status, Frame } from "../types";
import {
  toFrame,
  resolveHandSlots,
  extractBlendshapes,
  isFaceEligibleTick,
  createLandmarkers,
  MediaPipeLandmarkerSet,
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
};

const MEDIAPIPE_STRIDE = 2;
const FPS_WINDOW = 60;
const CAPTURE_WIDTH = 640;
const CAPTURE_HEIGHT = 360;

export function useMediaPipeTasks({ onFrame }: UseMediaPipeTasksOptions = {}) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const onFrameRef = useRef(onFrame);
  const landmarkersRef = useRef<MediaPipeLandmarkerSet | null>(null);
  const isSendingRef = useRef(false);
  const streamRef = useRef<MediaStream | null>(null);
  const frameIndexRef = useRef(0);
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
    let isMounted = true;
    import("@mediapipe/tasks-vision")
      .then((visionModule) => createLandmarkers(visionModule))
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
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
        streamRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    const loop = () => {
      if (cancelled) return;
      const landmarkers = landmarkersRef.current;
      const video = videoRef.current;
      if (landmarkers && video && video.readyState >= 2 && !isSendingRef.current) {
        frameIndexRef.current++;
        if (frameIndexRef.current % MEDIAPIPE_STRIDE === 0) {
          isSendingRef.current = true;
          eligibleTickRef.current++;
          const ts = performance.now();
          try {
            const poseResult = landmarkers.pose.detectForVideo(video, ts);
            const handResult = landmarkers.hand.detectForVideo(video, ts);
            const { left, right } = resolveHandSlots(handResult.landmarks, handResult.handedness);

            if (isFaceEligibleTick(eligibleTickRef.current)) {
              const faceResult = landmarkers.face.detectForVideo(video, ts);
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
