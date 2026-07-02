"use client";

import { useEffect, useRef, useState, useCallback } from "react";

const API_URL = "http://localhost:8000/predict";
const CAPTURE_API_URL = "http://localhost:8000/capture";
const STATS_API_URL = "http://localhost:8000/dataset_stats";
const RECORDING_MAX_FRAMES = 60;
const NUM_LANDMARKS = 75;

const PILOT_LABELS = [
  { value: "dolor", label: "Dolor" },
  { value: "doctor", label: "Doctor" },
  { value: "ayuda", label: "Ayuda" },
  { value: "revisar", label: "Revisar" },
  { value: "respirar", label: "Respirar" },
];

type Landmark = [number, number, number, number]; // x, y, z, visibility
type Frame = Landmark[];

type PredictionResult = {
  sign: string;
  confidence: number;
  top3: { sign: string; confidence: number }[];
} | null;

type HandDetection = { left: boolean; right: boolean };

type Status = "idle" | "loading" | "recording" | "processing" | "done" | "error";

// ─── MediaPipe helpers loaded from CDN ─────────────────────────────────────
declare global {
  interface Window {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    Holistic: any;
    drawConnectors: (ctx: CanvasRenderingContext2D, landmarks: unknown, connections: unknown, style?: unknown) => void;
    drawLandmarks: (ctx: CanvasRenderingContext2D, landmarks: unknown, style?: unknown) => void;
    POSE_CONNECTIONS: unknown;
    HAND_CONNECTIONS: unknown;
    FACEMESH_TESSELATION: unknown;
  }
}

export default function HomePage() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const holisticRef = useRef<any>(null);
  const recordedFrames = useRef<Frame[]>([]);
  const isRecording = useRef(false);
  const frameIndexRef = useRef(0); // for throttling MediaPipe calls
  const handleStopRecordingRef = useRef<() => void>(() => {});
  const isPredictingRef = useRef(false);
  const framesSinceLastPredictRef = useRef(0);
  const triggerRealtimePredictionRef = useRef<(frames: Frame[]) => void>(() => {});

  const [status, setStatus] = useState<Status>("loading");
  const [mode, setMode] = useState<"predict" | "capture">("predict");
  const modeRef = useRef(mode);
  const [captureLabel, setCaptureLabel] = useState<string>("dolor");
  const [capturedCount, setCapturedCount] = useState(0);

  const [prediction, setPrediction] = useState<PredictionResult>(null);
  const [frameCount, setFrameCount] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [hands, setHands] = useState<HandDetection>({ left: false, right: false });

  // ─── Draw skeleton on canvas ──────────────────────────────────────────────
  const onResults = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (results: any) => {
      const canvas = canvasRef.current;
      const video = videoRef.current;
      if (!canvas || !video) return;

      const ctx = canvas.getContext("2d");
      if (!ctx) return;

      canvas.width = video.videoWidth || 640;
      canvas.height = video.videoHeight || 480;

      ctx.save();
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(results.image, 0, 0, canvas.width, canvas.height);

      // Draw landmarks
      if (window.drawConnectors) {
        window.drawConnectors(ctx, results.poseLandmarks, window.POSE_CONNECTIONS, { color: "#4f46e5", lineWidth: 2 });
        window.drawLandmarks(ctx, results.poseLandmarks, { color: "#818cf8", lineWidth: 1, radius: 2 });
        window.drawConnectors(ctx, results.rightHandLandmarks, window.HAND_CONNECTIONS, { color: "#10b981", lineWidth: 2 });
        window.drawLandmarks(ctx, results.rightHandLandmarks, { color: "#6ee7b7", lineWidth: 1, radius: 2 });
        window.drawConnectors(ctx, results.leftHandLandmarks, window.HAND_CONNECTIONS, { color: "#f59e0b", lineWidth: 2 });
        window.drawLandmarks(ctx, results.leftHandLandmarks, { color: "#fcd34d", lineWidth: 1, radius: 2 });
      }
      ctx.restore();

      // Track hand detection state
      setHands({ left: !!results.leftHandLandmarks, right: !!results.rightHandLandmarks });

      // ─── Collect keypoints ───────────────────────────────
      const currentMode = modeRef.current;
      if (currentMode === "capture" && !isRecording.current) return;

      // IMPORTANT: match extract_keypoints.py zero-padding exactly:
      // pose visibility comes from MediaPipe (0-1), hands default to 0 when not detected
      const extractLandmarks = (lms: { x: number; y: number; z: number; visibility?: number }[] | undefined, n: number, defaultVis = 0): Landmark[] => {
        if (!lms || lms.length === 0) return Array.from({ length: n }, () => [0, 0, 0, defaultVis] as Landmark);
        return lms.map((l) => [l.x, l.y, l.z, l.visibility ?? defaultVis] as Landmark);
      };

      const pose = extractLandmarks(results.poseLandmarks, 33, 0);
      const leftHand = extractLandmarks(results.leftHandLandmarks, 21, 0);
      const rightHand = extractLandmarks(results.rightHandLandmarks, 21, 0);
      const frame: Frame = [...pose, ...leftHand, ...rightHand]; // 75 landmarks

      recordedFrames.current.push(frame);

      if (currentMode === "predict") {
        if (recordedFrames.current.length > RECORDING_MAX_FRAMES) {
          recordedFrames.current.shift();
        }
        
        framesSinceLastPredictRef.current++;
        if (recordedFrames.current.length === RECORDING_MAX_FRAMES && framesSinceLastPredictRef.current >= 15) {
          if (!isPredictingRef.current) {
            framesSinceLastPredictRef.current = 0;
            triggerRealtimePredictionRef.current([...recordedFrames.current]);
          }
        }
      } else {
        setFrameCount(recordedFrames.current.length);
        if (recordedFrames.current.length >= RECORDING_MAX_FRAMES) {
          isRecording.current = false;
          handleStopRecordingRef.current();
        }
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    []
  );

  // ─── Send to API ──────────────────────────────────────────────────────────
  const handleStopRecording = useCallback(async () => {
    const frames = [...recordedFrames.current];
    recordedFrames.current = [];
    setFrameCount(0);
    setStatus("processing");
    setPrediction(null);
    setError(null);

    try {
      if (mode === "predict") {
        const res = await fetch(API_URL, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ frames }),
        });
        if (!res.ok) throw new Error(`API error ${res.status}`);
        const data: PredictionResult = await res.json();
        setPrediction(data);
      } else {
        const res = await fetch(CAPTURE_API_URL, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ label: captureLabel, frames }),
        });
        if (!res.ok) throw new Error(`API error ${res.status}`);
        const data = await res.json();
        setCapturedCount(data.samples_for_label);
      }
      setStatus("done");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
      setStatus("error");
    }
  }, [mode, captureLabel]);

  const triggerRealtimePrediction = useCallback(async (frames: Frame[]) => {
    isPredictingRef.current = true;
    try {
      const res = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ frames }),
      });
      if (res.ok) {
        const data = await res.json();
        setPrediction(data);
      }
    } catch (e) {
      console.error("Realtime prediction error:", e);
    } finally {
      isPredictingRef.current = false;
    }
  }, []);

  useEffect(() => {
    handleStopRecordingRef.current = handleStopRecording;
    triggerRealtimePredictionRef.current = triggerRealtimePrediction;
  }, [handleStopRecording, triggerRealtimePrediction]);

  useEffect(() => {
    modeRef.current = mode;
    recordedFrames.current = [];
    framesSinceLastPredictRef.current = 0;
    if (mode === "predict") {
      setStatus("idle");
    }
  }, [mode]);

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(STATS_API_URL);
      if (res.ok) {
        const stats = await res.json();
        setCapturedCount(stats[captureLabel] || 0);
      }
    } catch (e) {
      console.error("Error fetching stats:", e);
    }
  }, [captureLabel]);

  useEffect(() => {
    if (mode === "capture") {
      fetchStats();
    }
  }, [mode, captureLabel, fetchStats]);

  // ─── Load MediaPipe and start camera ──────────────────────────────────────
  useEffect(() => {
    const scripts = [
      "https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils/camera_utils.js",
      "https://cdn.jsdelivr.net/npm/@mediapipe/drawing_utils/drawing_utils.js",
      "https://cdn.jsdelivr.net/npm/@mediapipe/holistic/holistic.js",
    ];

    let loadedCount = 0;

    const initMediaPipe = () => {
      const holistic = new window.Holistic({
        locateFile: (file: string) =>
          `https://cdn.jsdelivr.net/npm/@mediapipe/holistic/${file}`,
      });

      holistic.setOptions({
        modelComplexity: 1,       // 1 = good balance of accuracy vs speed
        smoothLandmarks: true,
        enableSegmentation: false,
        minDetectionConfidence: 0.4,
        minTrackingConfidence: 0.4,
      });

      holistic.onResults(onResults);
      holisticRef.current = holistic;

      navigator.mediaDevices
        .getUserMedia({ video: { width: 1280, height: 720 } })
        .then((stream) => {
          if (videoRef.current) {
            videoRef.current.srcObject = stream;
            videoRef.current.onloadedmetadata = () => {
              videoRef.current!.play();
              setStatus("idle");
              startLoop();
            };
          }
        })
        .catch(() => {
          setError("No se pudo acceder a la cámara. Verifica los permisos del navegador.");
          setStatus("error");
        });
    };

    const startLoop = () => {
      // Send to MediaPipe every 2 frames (~30fps inference on a 60fps camera)
      // This keeps the UI thread free and prevents FPS drops.
      const MEDIAPIPE_STRIDE = 2;
      const loop = async () => {
        frameIndexRef.current++;
        if (
          videoRef.current &&
          holisticRef.current &&
          videoRef.current.readyState >= 2 &&
          frameIndexRef.current % MEDIAPIPE_STRIDE === 0
        ) {
          await holisticRef.current.send({ image: videoRef.current });
        }
        requestAnimationFrame(loop);
      };
      requestAnimationFrame(loop);
    };

    const loadScript = (src: string) => {
      const script = document.createElement("script");
      script.src = src;
      script.crossOrigin = "anonymous";
      script.onload = () => {
        loadedCount++;
        if (loadedCount === scripts.length) initMediaPipe();
      };
      document.head.appendChild(script);
    };

    scripts.forEach(loadScript);
  }, [onResults]);

  // ─── Button handlers ──────────────────────────────────────────────────────
  const handleStart = () => {
    recordedFrames.current = [];
    setFrameCount(0);
    setPrediction(null);
    setError(null);
    isRecording.current = true;
    setStatus("recording");
  };

  const handleStop = () => {
    isRecording.current = false;
    if (recordedFrames.current.length >= 5) {
      handleStopRecording();
    } else {
      setStatus("idle");
    }
  };

  // ─── UI ───────────────────────────────────────────────────────────────────
  const isIdle = status === "idle" || status === "done" || status === "error";

  return (
    <main className="min-h-screen bg-[#0a0a0a] text-white flex flex-col items-center justify-center p-6 gap-8">
      {/* Header */}
      <div className="text-center">
        <h1 className="text-3xl font-semibold tracking-tight text-white">Nexora</h1>
        <p className="text-sm text-neutral-500 mt-1">Reconocimiento de Lengua de Señas Argentina</p>
      </div>

      {/* Mode Selector */}
      <div className="flex bg-neutral-900 border border-neutral-800 rounded-xl p-1 gap-1">
        <button
          onClick={() => setMode("predict")}
          className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
            mode === "predict" ? "bg-indigo-600 text-white" : "text-neutral-400 hover:text-white"
          }`}
        >
          Inferencia
        </button>
        <button
          onClick={() => setMode("capture")}
          className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
            mode === "capture" ? "bg-indigo-600 text-white" : "text-neutral-400 hover:text-white"
          }`}
        >
          Capturar Dataset
        </button>
      </div>

      {mode === "capture" && (
        <div className="flex items-center gap-4 bg-neutral-900 border border-neutral-800 p-3 rounded-xl w-full max-w-2xl">
          <label className="text-sm font-medium text-neutral-300">Seña a grabar:</label>
          <select
            value={captureLabel}
            onChange={(e) => setCaptureLabel(e.target.value)}
            className="bg-neutral-950 border border-neutral-800 text-white text-sm rounded-lg block w-full p-2.5 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
            disabled={!isIdle}
          >
            {PILOT_LABELS.map((l) => (
              <option key={l.value} value={l.value}>
                {l.label}
              </option>
            ))}
          </select>
          <div className="flex flex-col text-right min-w-[80px]">
            <span className="text-xs text-neutral-500">Muestras</span>
            <span className="text-lg font-semibold text-indigo-400">{capturedCount}</span>
          </div>
        </div>
      )}

      {/* Camera + Canvas */}
      <div className="relative w-full max-w-2xl aspect-video rounded-2xl overflow-hidden bg-neutral-900 border border-neutral-800">
        <video ref={videoRef} className="absolute inset-0 w-full h-full object-cover opacity-0" playsInline muted />
        <canvas ref={canvasRef} className="absolute inset-0 w-full h-full object-cover" />

        {/* Loading overlay */}
        {status === "loading" && (
          <div className="absolute inset-0 flex items-center justify-center bg-neutral-900">
            <div className="flex flex-col items-center gap-3 text-neutral-500">
              <div className="w-8 h-8 border-2 border-neutral-600 border-t-indigo-500 rounded-full animate-spin" />
              <span className="text-sm">Iniciando cámara y MediaPipe…</span>
            </div>
          </div>
        )}

        {/* Hand detection indicators */}
        <div className="absolute top-4 right-4 flex gap-2">
          <span className={`text-xs px-2 py-1 rounded-full font-medium ${ hands.left ? "bg-amber-500/80 text-white" : "bg-neutral-800/80 text-neutral-500" }`}>L</span>
          <span className={`text-xs px-2 py-1 rounded-full font-medium ${ hands.right ? "bg-emerald-500/80 text-white" : "bg-neutral-800/80 text-neutral-500" }`}>R</span>
        </div>

        {/* Recording indicator */}
        {status === "recording" && (
          <div className="absolute top-4 left-4 flex items-center gap-2 bg-black/60 backdrop-blur-sm px-3 py-1.5 rounded-full">
            <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
            <span className="text-xs text-white font-medium">
              {frameCount} / {RECORDING_MAX_FRAMES} frames
            </span>
          </div>
        )}

        {/* Processing overlay */}
        {status === "processing" && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/50 backdrop-blur-sm">
            <div className="w-8 h-8 border-2 border-neutral-600 border-t-indigo-500 rounded-full animate-spin" />
          </div>
        )}
      </div>

      {/* Result card */}
      {prediction && mode === "predict" && (
        <div className="w-full max-w-2xl bg-neutral-900 border border-neutral-800 rounded-2xl p-6">
          <div className="flex items-baseline justify-between">
            <span className="text-2xl font-semibold capitalize">{prediction.sign}</span>
            <span className="text-lg font-medium text-indigo-400">{prediction.confidence.toFixed(1)}%</span>
          </div>
          {/* Confidence bar */}
          <div className="mt-3 h-1.5 w-full bg-neutral-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-indigo-500 rounded-full transition-all duration-500"
              style={{ width: `${prediction.confidence}%` }}
            />
          </div>
          {/* Top-3 */}
          <div className="mt-4 space-y-2">
            {prediction.top3.slice(1).map((item) => (
              <div key={item.sign} className="flex items-center justify-between text-sm text-neutral-500">
                <span className="capitalize">{item.sign}</span>
                <span>{item.confidence.toFixed(1)}%</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Error */}
      {status === "error" && error && (
        <p className="text-sm text-red-400 bg-red-950/40 border border-red-900/50 px-4 py-2 rounded-xl">{error}</p>
      )}

      {/* Controls */}
      {mode === "capture" && (
        <div className="flex gap-3">
          {isIdle && (
            <button
              id="btn-start-sign"
              onClick={handleStart}
              className="px-6 py-3 bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 text-white text-sm font-medium rounded-xl transition-colors cursor-pointer"
            >
              Empezar captura
            </button>
          )}
          {status === "recording" && (
            <button
              id="btn-stop-sign"
              onClick={handleStop}
              className="px-6 py-3 bg-neutral-800 hover:bg-neutral-700 text-white text-sm font-medium rounded-xl transition-colors cursor-pointer"
            >
              Detener y guardar
            </button>
          )}
        </div>
      )}

      {/* Status hint */}
      <p className="text-xs text-neutral-600 text-center max-w-md">
        {status === "idle" && mode === "predict" && 'Hacé la seña frente a la cámara. La inferencia es automática.'}
        {status === "idle" && mode === "capture" && 'Presioná "Empezar captura", realizá el movimiento y luego "Detener y guardar".'}
        {status === "recording" && "Realizá la seña ahora…"}
        {status === "processing" && mode === "capture" && "Guardando…"}
        {status === "done" && mode === "capture" && "Muestra guardada correctamente."}
      </p>
    </main>
  );
}
