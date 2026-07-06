import { useEffect, useRef, useState } from "react";
import { Status, Frame, Landmark } from "../types";

declare global {
  interface Window {
    Camera: any;
    Holistic: any;
    drawConnectors: any;
    drawLandmarks: any;
    POSE_CONNECTIONS: any;
    HAND_CONNECTIONS: any;
  }
}

type UseMediaPipeOptions = {
  onFrame?: (frame: Frame) => void;
  drawLandmarksOnCanvas?: boolean;
};

export function useMediaPipe({ onFrame, drawLandmarksOnCanvas = true }: UseMediaPipeOptions = {}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const holisticRef = useRef<any>(null);
  const frameIndexRef = useRef(0);
  const isProcessingRef = useRef(false);
  const onFrameRef = useRef(onFrame);
  const drawLandmarksRef = useRef(drawLandmarksOnCanvas);
  const [status, setStatus] = useState<Status>("loading");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    onFrameRef.current = onFrame;
  }, [onFrame]);

  useEffect(() => {
    drawLandmarksRef.current = drawLandmarksOnCanvas;
  }, [drawLandmarksOnCanvas]);

  useEffect(() => {
    let camera: any = null;
    let isComponentMounted = true;
    let retryTimeout: NodeJS.Timeout;

    const init = () => {
      if (typeof window === "undefined") return;

      // Wait for MediaPipe scripts to load (afterInteractive strategy)
      if (!window.Holistic) {
        retryTimeout = setTimeout(init, 500);
        return;
      }

      try {
        const holistic = new window.Holistic({
          locateFile: (file: string) =>
            `https://cdn.jsdelivr.net/npm/@mediapipe/holistic/${file}`,
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

          const canvasElement = canvasRef.current;
          const videoElement = videoRef.current;
          
          if (canvasElement && videoElement) {
            const ctx = canvasElement.getContext("2d");
            if (ctx) {
              // Only resize when dimensions actually change (avoids context reset per frame)
              if (videoElement.videoWidth > 0 && canvasElement.width !== videoElement.videoWidth) {
                canvasElement.width = videoElement.videoWidth;
                canvasElement.height = videoElement.videoHeight;
              }

              ctx.save();
              ctx.clearRect(0, 0, canvasElement.width, canvasElement.height);
              ctx.drawImage(results.image, 0, 0, canvasElement.width, canvasElement.height);

              if (window.drawConnectors && drawLandmarksRef.current) {
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
              }
              ctx.restore();
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
          isProcessingRef.current = false;
        });

        // Accurate camera loop synchronized to hardware frame rate
        let lastVideoTime = -1;
        const MEDIAPIPE_STRIDE = 2;
        const startLoop = () => {
          const loop = async () => {
            if (!isComponentMounted) return;
            
            if (
              videoRef.current &&
              holisticRef.current &&
              videoRef.current.readyState >= 2
            ) {
              const currentTime = videoRef.current.currentTime;
              if (currentTime !== lastVideoTime) {
                lastVideoTime = currentTime;
                frameIndexRef.current++;
                if (frameIndexRef.current % MEDIAPIPE_STRIDE === 0) {
                  try {
                    await holisticRef.current.send({ image: videoRef.current });
                  } catch (e) {
                    console.error(e);
                  }
                }
              }
            }
            requestAnimationFrame(loop);
          };
          requestAnimationFrame(loop);
        };

        navigator.mediaDevices
          .getUserMedia({
            video: {
              width: { ideal: 640 },
              height: { ideal: 480 },
              frameRate: { ideal: 30 },
            },
          })
          .then((stream) => {
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
    };
  }, []);

  return { videoRef, canvasRef, status, setStatus, error };
}
