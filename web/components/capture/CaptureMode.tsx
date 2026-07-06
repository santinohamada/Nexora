import { useState, memo } from "react";
import { Status } from "../../types";

export const CaptureMode = memo(function CaptureMode({
  canvasRef,
  status,
  setStatus,
  setMode,
}: {
  canvasRef: React.RefObject<HTMLCanvasElement | null>;
  status: Status;
  setStatus: React.Dispatch<React.SetStateAction<Status>>;
  setMode: (mode: "predict" | "capture") => void;
}) {
  const [captureLabel, setCaptureLabel] = useState("ayuda");
  const [repeatCount, setRepeatCount] = useState<number>(1);
  const [countdown, setCountdown] = useState<number | null>(null);

  const labels = [
    { value: "ayuda", label: "Ayuda" },
    { value: "dolor", label: "Dolor" },
    { value: "doctor", label: "Doctor" },
  ];

  const isIdle = status === "idle" || status === "done" || status === "error";

  const handleStartSequence = async () => {
    // Basic implementation since actual recording logic is complex
    console.log("Start recording", captureLabel, repeatCount);
  };

  const handleStop = () => {
    setStatus("idle");
    setCountdown(null);
  };

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900 flex flex-col p-6 gap-4">
      <div className="flex justify-between items-center bg-white p-4 rounded-2xl shadow-sm">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full border-4 border-indigo-600 flex items-center justify-center">
            <div className="w-4 h-4 rounded-full border-2 border-indigo-400"></div>
          </div>
          <h1 className="text-xl font-bold tracking-tight text-indigo-900">
            NEXORA
          </h1>
        </div>
        <button
          onClick={() => setMode("predict")}
          className="px-4 py-2 bg-slate-100 rounded-xl text-sm font-medium hover:bg-slate-200"
        >
          Volver a Inferencia
        </button>
      </div>

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
        <div className="relative w-full aspect-video rounded-2xl overflow-hidden bg-slate-900">
          {/* Video stays in page.tsx — only canvas is rendered here */}
          <canvas
            ref={canvasRef as any}
            className="absolute inset-0 w-full h-full object-cover"
          />

          {status === "loading" && (
            <div className="absolute inset-0 flex items-center justify-center bg-slate-900">
              <span className="text-sm text-slate-400">
                Iniciando cámara...
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
    </main>
  );
});
