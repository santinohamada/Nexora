import { useState, useRef, useEffect, memo } from "react";
import { Status, Frame } from "../../types";
import Image from "next/image";
import { Plus, Tag, Search } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const RECORDING_SAMPLE_LENGTH = 45;

type DatasetStats = Record<string, number>;
type MediaPipeBackend = "legacy" | "tasks";

export const CaptureMode = memo(function CaptureMode({
  videoRef,
  canvasRef,
  status,
  setStatus,
  setMode,
  captureHandlerRef,
  backend,
}: {
  videoRef: (node: HTMLVideoElement | null) => void;
  canvasRef: React.RefObject<HTMLCanvasElement | null>;
  status: Status;
  setStatus: React.Dispatch<React.SetStateAction<Status>>;
  setMode: (mode: "predict" | "capture") => void;
  captureHandlerRef: React.MutableRefObject<((f: Frame, blendshapes?: number[]) => void) | null>;
  backend: MediaPipeBackend;
}) {

  const [captureLabel, setCaptureLabel] = useState("");
  const [newLabel, setNewLabel] = useState("");
  const [repeatCount, setRepeatCount] = useState<number>(1);
  const [countdown, setCountdown] = useState<number | null>(null);
  const [knownLabels, setKnownLabels] = useState<string[]>([]);
  const [datasetStats, setDatasetStats] = useState<DatasetStats>({});
  const [showNewInput, setShowNewInput] = useState(false);
  const [searchFilter, setSearchFilter] = useState("");
  const [currentRepeat, setCurrentRepeat] = useState(0);

  const fetchLabelsAndStats = () => {
    // Fetch known classes from model
    fetch(`${API_URL}/classes`)
      .then((res) => res.json())
      .then((data: string[]) => {
        const filtered = data.filter((c) => c !== "idle");
        setKnownLabels(filtered);
        if (filtered.length > 0 && !captureLabel) {
          setCaptureLabel(filtered[0]);
        }
      })
      .catch((err) => console.error("Error fetching classes:", err));

    // Fetch dataset stats (includes labels not yet in model)
    fetch(`${API_URL}/dataset_stats?mode=${backend}`)
      .then((res) => res.json())
      .then((stats: DatasetStats) => {
        setDatasetStats(stats);
        // Merge dataset labels into known labels
        const datasetLabels = Object.keys(stats);
        setKnownLabels((prev) => {
          const merged = new Set([...prev, ...datasetLabels]);
          merged.delete("idle");
          return Array.from(merged).sort();
        });
      })
      .catch((err) => console.error("Error fetching stats:", err));
  };

  useEffect(() => {
    fetchLabelsAndStats();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const isRecordingRef = useRef(false);
  const recordedFramesRef = useRef<Frame[]>([]);
  const recordedBlendshapesRef = useRef<number[][]>([]);
  const resolveRecordingRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    captureHandlerRef.current = (frame: Frame, blendshapes?: number[]) => {
      if (isRecordingRef.current) {
        recordedFramesRef.current.push(frame);
        if (backend === "tasks" && blendshapes) {
          recordedBlendshapesRef.current.push(blendshapes);
        }
        if (recordedFramesRef.current.length >= RECORDING_SAMPLE_LENGTH) {
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
  }, [captureHandlerRef, backend]);

  const isIdle = status === "idle" || status === "done" || status === "error";

  const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

  const recordOneSample = async () => {
    for (let i = 3; i > 0; i--) {
      setCountdown(i);
      await sleep(1000);
    }
    setCountdown(null);
    setStatus("recording");

    recordedFramesRef.current = [];
    recordedBlendshapesRef.current = [];
    isRecordingRef.current = true;

    await new Promise<void>((resolve) => {
      resolveRecordingRef.current = resolve;
    });

    setStatus("loading");
    try {
      await fetch(`${API_URL}/capture`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          label: captureLabel,
          mode: backend,
          frames: recordedFramesRef.current,
          ...(backend === "tasks" ? { blendshapes: recordedBlendshapesRef.current } : {}),
        }),
      });
    } catch (err) {
      console.error(err);
    }
  };

  const handleStartSequence = async () => {
    if (!captureLabel.trim()) return;
    setCurrentRepeat(1);
    for (let i = 0; i < repeatCount; i++) {
      setCurrentRepeat(i + 1);
      await recordOneSample();
      if (i < repeatCount - 1) {
        setStatus("idle");
        await sleep(1000);
      }
    }
    setStatus("done");
    fetchLabelsAndStats(); // Refresh counts
    setTimeout(() => {
      setStatus("idle");
      setCurrentRepeat(0);
    }, 2000);
  };

  const handleStop = () => {
    setStatus("idle");
    setCountdown(null);
    setCurrentRepeat(0);
    isRecordingRef.current = false;
    if (resolveRecordingRef.current) {
      resolveRecordingRef.current();
      resolveRecordingRef.current = null;
    }
  };

  const handleAddNewLabel = () => {
    const label = newLabel.trim().toLowerCase();
    if (!label) return;
    if (knownLabels.includes(label)) {
      setCaptureLabel(label);
      setNewLabel("");
      setShowNewInput(false);
      return;
    }
    setKnownLabels((prev) => [...prev, label].sort());
    setCaptureLabel(label);
    setNewLabel("");
    setShowNewInput(false);
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

        {/* Label selector */}
        <div className="w-full">
          <div className="flex items-center justify-between mb-2">
            <label className="text-sm font-medium text-slate-700 flex items-center gap-1.5">
              <Tag size={14} />
              Seña a grabar:
            </label>
            <button
              onClick={() => setShowNewInput(!showNewInput)}
              disabled={!isIdle}
              className="flex items-center gap-1 text-xs font-medium text-indigo-600 hover:text-indigo-800 transition-colors disabled:opacity-40"
            >
              <Plus size={14} />
              Nueva seña
            </button>
          </div>

          {/* New label input */}
          {showNewInput && (
            <div className="flex gap-2 mb-3">
              <input
                type="text"
                value={newLabel}
                onChange={(e) => setNewLabel(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleAddNewLabel()}
                placeholder="Nombre de la nueva seña..."
                className="flex-1 bg-slate-100 border border-slate-200 text-sm rounded-lg p-2.5 outline-none focus:border-indigo-400 transition-colors"
                disabled={!isIdle}
                autoFocus
              />
              <button
                onClick={handleAddNewLabel}
                disabled={!newLabel.trim() || !isIdle}
                className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg font-medium hover:bg-indigo-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Agregar
              </button>
            </div>
          )}

          {/* Search filter */}
          {knownLabels.length > 6 && (
            <div className="relative mb-2">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                value={searchFilter}
                onChange={(e) => setSearchFilter(e.target.value)}
                placeholder="Buscar seña..."
                className="w-full bg-slate-100 border border-slate-200 text-sm rounded-lg pl-8 pr-3 py-2 outline-none focus:border-indigo-400 transition-colors"
              />
            </div>
          )}

          {/* Label chips */}
          <div className="flex flex-wrap gap-2 max-h-40 overflow-y-auto pr-1">
            {knownLabels
              .filter((l) => !searchFilter || l.includes(searchFilter.toLowerCase()))
              .map((label) => (
              <button
                key={label}
                onClick={() => isIdle && setCaptureLabel(label)}
                disabled={!isIdle}
                className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all border ${
                  captureLabel === label
                    ? "bg-indigo-600 text-white border-indigo-600 shadow-sm"
                    : "bg-slate-100 text-slate-600 border-slate-200 hover:border-indigo-300 hover:bg-indigo-50"
                } disabled:opacity-60 disabled:cursor-not-allowed`}
              >
                {label}
                {datasetStats[label] !== undefined && (
                  <span className={`ml-1.5 text-xs ${
                    captureLabel === label ? "text-indigo-200" : "text-slate-400"
                  }`}>
                    ({datasetStats[label]})
                  </span>
                )}
              </button>
            ))}
            {knownLabels.length === 0 && (
              <p className="text-sm text-slate-400">
                No hay señas registradas. Creá una nueva con el botón de arriba.
              </p>
            )}
          </div>
        </div>

        {/* Video preview */}
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
          {currentRepeat > 0 && repeatCount > 1 && (
            <div className="absolute top-4 right-4 z-30 bg-indigo-600/90 text-white px-3 py-1.5 rounded-full shadow-lg text-xs font-bold tracking-wide backdrop-blur-sm">
              MUESTRA {currentRepeat} / {repeatCount}
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

        {/* Controls */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <label className="text-sm text-slate-500">Repeticiones:</label>
            <input
              type="number"
              value={repeatCount}
              onChange={(e) => setRepeatCount(parseInt(e.target.value) || 1)}
              className="bg-slate-100 rounded-lg p-2 w-20 text-center outline-none"
              min="1"
              disabled={!isIdle}
            />
          </div>
          {isIdle && countdown === null ? (
            <button
              onClick={handleStartSequence}
              disabled={!captureLabel.trim()}
              className="px-6 py-2 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
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

        {/* Selected label indicator */}
        {captureLabel && (
          <p className="text-sm text-slate-500">
            Grabando para: <span className="font-semibold text-indigo-600">{captureLabel}</span>
            {datasetStats[captureLabel] !== undefined && (
              <span className="ml-1">({datasetStats[captureLabel]} muestras)</span>
            )}
            {datasetStats[captureLabel] === undefined && (
              <span className="ml-1 text-amber-600">(nueva — la carpeta se crea al grabar)</span>
            )}
          </p>
        )}
      </div>
    </div>
  </main>
);
});
