import { useState, useRef, useEffect, memo } from "react";
import { Status } from "../../types";
import Image from "next/image";

export const CaptureMode = memo(function CaptureMode({
  videoRef,
  canvasRef,
  status,
  setStatus,
  setMode,
  captureHandlerRef,
}: {
  videoRef: (node: HTMLVideoElement | null) => void;
  canvasRef: React.RefObject<HTMLCanvasElement | null>;
  status: Status;
  setStatus: React.Dispatch<React.SetStateAction<Status>>;
  setMode: (mode: "predict" | "capture") => void;
  captureHandlerRef: React.MutableRefObject<((f: any) => void) | null>;
}) {


  const [captureLabel, setCaptureLabel] = useState("");
  const [repeatCount, setRepeatCount] = useState<number>(1);
  const [countdown, setCountdown] = useState<number | null>(null);
  const [labels, setLabels] = useState<{value: string, label: string}[]>([]);

  useEffect(() => {
    fetch("http://localhost:8000/classes")
      .then((res) => res.json())
      .then((data: string[]) => {
        // Filter out idle or keep it if they want to train idle
        const options = data.map((c) => ({
          value: c,
          label: c.charAt(0).toUpperCase() + c.slice(1),
        }));
        setLabels(options);
        if (options.length > 0) {
          setCaptureLabel(options[0].value);
        }
      })
      .catch((err) => console.error("Error fetching classes:", err));
  }, []);

  const isRecordingRef = useRef(false);
  const recordedFramesRef = useRef<any[]>([]);
  const resolveRecordingRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    captureHandlerRef.current = (frame: any) => {
      if (isRecordingRef.current) {
        recordedFramesRef.current.push(frame);
        if (recordedFramesRef.current.length >= 45) {
          isRecordingRef.current = false;
          if (resolveRecordingRef.current) {
            resolveRecordingRef.current();
            resolveRecordingRef.current = null;
          }
        }
      }
    };
    return () => {
      captureHandlerRef.current = null;
    };
  }, [captureHandlerRef]);

  const isIdle = status === "idle" || status === "done" || status === "error";

  const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

  const recordOneSample = async () => {
    // Countdown
    for (let i = 3; i > 0; i--) {
      setCountdown(i);
      await sleep(1000);
    }
    setCountdown(null);
    setStatus("recording");

    // Record frames
    recordedFramesRef.current = [];
    isRecordingRef.current = true;
    
    // Wait until frames are collected
    await new Promise<void>((resolve) => {
      resolveRecordingRef.current = resolve;
    });

    // POST
    setStatus("loading");
    try {
      await fetch("http://localhost:8000/capture", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          label: captureLabel,
          frames: recordedFramesRef.current,
        }),
      });
    } catch (err) {
      console.error(err);
    }
  };

  const handleStartSequence = async () => {
    for (let i = 0; i < repeatCount; i++) {
      await recordOneSample();
      if (i < repeatCount - 1) {
        setStatus("idle");
        await sleep(1000); // Wait 1s between repetitions
      }
    }
    setStatus("done");
    setTimeout(() => setStatus("idle"), 2000);
  };

  const handleStop = () => {
    setStatus("idle");
    setCountdown(null);
    isRecordingRef.current = false;
    if (resolveRecordingRef.current) {
      resolveRecordingRef.current();
      resolveRecordingRef.current = null;
    }
  };

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900 flex flex-col">
      <header className="flex justify-between items-center px-8 py-4 bg-white/50 backdrop-blur-md border-b border-slate-200/50 sticky top-0 z-50">
        <div className="flex items-center gap-3">
          <Image
            src="/Imagotipo NEXORA_Final.png"
            alt="NEXORA Logo"
            width={100}
            height={100}
            className="h-16 w-auto object-contain"
            priority
          />
        </div>
        <button
          onClick={() => setMode("predict")}
          className="px-5 py-2 bg-slate-900 text-white rounded-full text-sm font-semibold hover:bg-slate-800 transition-colors shadow-sm"
        >
          Volver a Inferencia
        </button>
      </header>

      <div className="flex-1 flex flex-col p-8 pb-20 max-w-[1600px] mx-auto w-full">

      <div className="bg-white p-6 rounded-2xl shadow-sm flex flex-col items-center gap-6 max-w-2xl mx-auto w-full mt-10">
        <h2 className="text-xl font-bold">Modo de Captura</h2>
        <div className="flex items-center gap-4 w-full">
          <label className="text-sm font-medium">Seña:</label>
          <select
            value={captureLabel}
            onChange={(e) => setCaptureLabel(e.target.value)}
            className="bg-slate-100 border border-slate-200 text-sm rounded-lg flex-1 p-2.5 outline-none"
            disabled={!isIdle}
          >
            {labels.map((l) => (
              <option key={l.value} value={l.value}>
                {l.label}
              </option>
            ))}
          </select>
        </div>
        <div className="relative w-full aspect-video rounded-2xl overflow-hidden bg-slate-900 flex items-center justify-center">
          {countdown !== null && (
            <div className="absolute inset-0 z-30 flex items-center justify-center bg-black/40">
              <span className="text-8xl font-bold text-white drop-shadow-lg">
                {countdown}
              </span>
            </div>
          )}
          {status === "recording" && (
            <div className="absolute top-4 left-4 z-30 flex items-center gap-2 bg-red-600/90 text-white px-3 py-1.5 rounded-full border border-red-500 animate-pulse shadow-lg">
              <span className="w-2.5 h-2.5 rounded-full bg-white animate-ping" />
              <span className="text-xs font-bold tracking-wide">GRABANDO</span>
            </div>
          )}

          <video
            ref={videoRef}
            className="absolute inset-0 w-full h-full object-cover z-0"
            playsInline
            muted
          />
          <canvas
            ref={canvasRef}
            className="absolute inset-0 w-full h-full object-cover z-10"
          />

          {status === "loading" && (
            <div className="absolute inset-0 z-20 flex items-center justify-center bg-slate-900/80">
              <span className="text-sm text-slate-300 font-medium">
                Procesando...
              </span>
            </div>
          )}
          {status === "done" && (
            <div className="absolute inset-0 z-20 flex items-center justify-center bg-emerald-900/80">
              <span className="text-xl text-emerald-300 font-bold">
                ¡Guardado!
              </span>
            </div>
          )}
        </div>
        <div className="flex gap-4">
          <input
            type="number"
            value={repeatCount}
            onChange={(e) => setRepeatCount(parseInt(e.target.value) || 1)}
            className="bg-slate-100 rounded-lg p-2 w-20 text-center outline-none"
            min="1"
            disabled={!isIdle}
          />
          {isIdle && countdown === null ? (
            <button
              onClick={handleStartSequence}
              className="px-6 py-2 bg-indigo-600 text-white rounded-lg font-medium"
            >
              Empezar
            </button>
          ) : (
            <button
              onClick={handleStop}
              className="px-6 py-2 bg-red-600 text-white rounded-lg font-medium"
            >
              Detener
            </button>
          )}
        </div>
      </div>
    </div>
  </main>
);
});
