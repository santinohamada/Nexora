import { useEffect, useRef, useState, useCallback } from "react";
import { Status, Frame, Landmark } from "../types";
import { loadScript } from "../lib/mediapipe";

declare global {
  interface Window {
    Holistic: any;
    drawConnectors: any;
    drawLandmarks: any;
    POSE_CONNECTIONS: any;
    HAND_CONNECTIONS: any;
  }
}

// Served from public/mediapipe/holistic (copied from node_modules by scripts/fetch-mediapipe-assets.mjs)
const HOLISTIC_BASE_PATH = "/mediapipe/holistic";
const HOLISTIC_SCRIPT_URL = `${HOLISTIC_BASE_PATH}/holistic.js`;
const DRAWING_UTILS_SCRIPT_URL = `${HOLISTIC_BASE_PATH}/drawing_utils.js`;

type UseMediaPipeOptions = {
  onFrame?: (frame: Frame) => void;
  drawLandmarksOnCanvas?: boolean;
  enabled?: boolean;
};

export function useMediaPipe({ onFrame, drawLandmarksOnCanvas = true, enabled = true }: UseMediaPipeOptions = {}) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const holisticRef = useRef<any>(null);
  const frameIndexRef = useRef(0);
  const onFrameRef = useRef(onFrame);
  const drawLandmarksRef = useRef(drawLandmarksOnCanvas);
  const ctxRef = useRef<CanvasRenderingContext2D | null>(null);
  const [status, setStatus] = useState<Status>("loading");
  const [error, setError] = useState<string | null>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const isSendingRef = useRef(false);
  const streamRef = useRef<MediaStream | null>(null);
  const sendTimestampRef = useRef<number | null>(null);
  const inferenceMsRef = useRef<number | null>(null);
  const latencyTimingEnabled =
    (typeof process !== "undefined" &&
      process.env.NEXT_PUBLIC_LATENCY_V2_TIMING === "on") ||
    false;

  // Callback ref: whenever React mounts a new <video> element (e.g. mode switch),
  // automatically re-attach the camera stream so it never goes black.
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
    if (!enabled) return;

    let isComponentMounted = true;
    let retryTimeout: NodeJS.Timeout;

    Promise.all([loadScript(HOLISTIC_SCRIPT_URL), loadScript(DRAWING_UTILS_SCRIPT_URL)]).catch(
      (err) => {
        console.warn("[Nexora] Failed to load MediaPipe Holistic scripts", err);
      }
    );

    const init = () => {
      if (typeof window === "undefined") return;

      if (!window.Holistic) {
        retryTimeout = setTimeout(init, 500);
        return;
      }

      try {
        const holistic = new window.Holistic({
          locateFile: (file: string) => `${HOLISTIC_BASE_PATH}/${file}`,
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

        holisticRef.current = holistic;

        holistic.onResults((results: any) => {
          if (!isComponentMounted) return;
          isSendingRef.current = false;

          if (latencyTimingEnabled && sendTimestampRef.current !== null) {
            const inferenceMs = performance.now() - sendTimestampRef.current;
            sendTimestampRef.current = null;
            inferenceMsRef.current = inferenceMs;
            console.debug(
              `[Nexora timing] stage=mediapipe_ms ms=${inferenceMs.toFixed(2)}`,
            );
          }

          const canvasElement = canvasRef.current;

          if (canvasElement) {
            // Cache context — invalidate if canvas element changed (mode switch)
            if (!ctxRef.current || ctxRef.current.canvas !== canvasElement) {
              ctxRef.current = canvasElement.getContext("2d");
            }
            const ctx = ctxRef.current;
            if (ctx) {
              const videoElement = videoRef.current;
              if (videoElement && videoElement.videoWidth > 0 && canvasElement.width !== videoElement.videoWidth) {
                canvasElement.width = videoElement.videoWidth;
                canvasElement.height = videoElement.videoHeight;
              }

              // Clear previous landmarks (canvas is transparent overlay on top of <video>)
              ctx.clearRect(0, 0, canvasElement.width, canvasElement.height);

              if (window.drawConnectors && drawLandmarksRef.current) {
                ctx.save();
                window.drawConnectors(
                  ctx,
                  results.poseLandmarks,
                  window.POSE_CONNECTIONS,
                  { color: "#4f46e5", lineWidth: 2 }
                );
                window.drawLandmarks(ctx, results.poseLandmarks, {
                  color: "#818cf8",
                  lineWidth: 1,
                  radius: 2,
                });
                window.drawConnectors(
                  ctx,
                  results.rightHandLandmarks,
                  window.HAND_CONNECTIONS,
                  { color: "#10b981", lineWidth: 2 }
                );
                window.drawLandmarks(ctx, results.rightHandLandmarks, {
                  color: "#6ee7b7",
                  lineWidth: 1,
                  radius: 2,
                });
                window.drawConnectors(
                  ctx,
                  results.leftHandLandmarks,
                  window.HAND_CONNECTIONS,
                  { color: "#f59e0b", lineWidth: 2 }
                );
                window.drawLandmarks(ctx, results.leftHandLandmarks, {
                  color: "#fcd34d",
                  lineWidth: 1,
                  radius: 2,
                });
                ctx.restore();
              }
            }
          }

          // Extract landmarks and notify listener
          if (onFrameRef.current) {
            const extractLandmarks = (
              lms:
                | { x: number; y: number; z: number; visibility?: number }[]
                | undefined,
              n: number,
              defaultVis = 0
            ): Landmark[] => {
              if (!lms || lms.length === 0)
                return Array.from(
                  { length: n },
                  () => [0, 0, 0, defaultVis] as Landmark
                );
              return lms
                .slice(0, n)
                .map(
                  (lm) =>
                    [lm.x, lm.y, lm.z, lm.visibility ?? defaultVis] as Landmark
                );
            };

            const pose = extractLandmarks(results.poseLandmarks, 33, 0);
            const leftHand = extractLandmarks(
              results.leftHandLandmarks,
              21,
              0
            );
            const rightHand = extractLandmarks(
              results.rightHandLandmarks,
              21,
              0
            );
            let frameData: Frame = [...pose, ...leftHand, ...rightHand];

            // Normalize relative to nose
            const nose = pose[0];
            if (nose) {
              frameData = frameData.map(
                (lm) =>
                  [
                    lm[0] - nose[0],
                    lm[1] - nose[1],
                    lm[2],
                    lm[3],
                  ] as Landmark
              );
            }

            onFrameRef.current(frameData);
          }
        });

        // Non-blocking loop: fire-and-forget send to MediaPipe
        // Does NOT use await — the rAF loop keeps running smoothly
        // while MediaPipe processes in the background
        const MEDIAPIPE_STRIDE = 2;
        const startLoop = () => {
          const loop = () => {
            if (!isComponentMounted) return;

            if (
              videoRef.current &&
              holisticRef.current &&
              videoRef.current.readyState >= 2 &&
              !isSendingRef.current
            ) {
              frameIndexRef.current++;
              if (frameIndexRef.current % MEDIAPIPE_STRIDE === 0) {
                isSendingRef.current = true;
                if (latencyTimingEnabled) {
                  sendTimestampRef.current = performance.now();
                }
                holisticRef.current.send({ image: videoRef.current }).catch(() => {
                  isSendingRef.current = false;
                });
              }
            }
            requestAnimationFrame(loop);
          };
          requestAnimationFrame(loop);
        };

        navigator.mediaDevices
          .getUserMedia({
            video: {
              width: { ideal: 1280 },
              height: { ideal: 720 },
              frameRate: { ideal: 30 },
            },
          })
          .then((stream) => {
            if (!isComponentMounted) {
              stream.getTracks().forEach((t) => t.stop());
              return;
            }
            streamRef.current = stream;
            setStream(stream);
            if (videoRef.current) {
              videoRef.current.srcObject = stream;
              videoRef.current.onloadedmetadata = () => {
                videoRef.current!.play();
                if (isComponentMounted) {
                  setStatus("idle");
                  startLoop();
                }
              };
            }
          })
          .catch(() => {
            if (isComponentMounted) {
              setError("No se pudo acceder a la cámara.");
              setStatus("error");
            }
          });
      } catch (err) {
        console.error(err);
        if (isComponentMounted) {
          setError("Error inicializando MediaPipe.");
          setStatus("error");
        }
      }
    };

    init();

    return () => {
      isComponentMounted = false;
      clearTimeout(retryTimeout);
      if (holisticRef.current) {
        try {
          holisticRef.current.close();
        } catch (e) {
          /* holistic may already be closed */
        }
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
        streamRef.current = null;
      }
    };
  }, [enabled]);

  return { videoRef: setVideoNode, canvasRef, status, setStatus, error, stream };
}
