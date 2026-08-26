"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { Camera, MonitorPlay, Trash2, Settings } from "lucide-react";
import { Header } from "../../components/layout/Header";
import { TopPredictions } from "../../components/camera/TopPredictions";
import { ChatBubble } from "../../components/chat/ChatBubble";
import { CaptureMode } from "../../components/capture/CaptureMode";
import { useMediaPipe } from "../../hooks/useMediaPipe";
import { useMediaPipeTasks } from "../../hooks/useMediaPipeTasks";
import { useSignWebSocket } from "../../hooks/useSignWebSocket";
import { useSentenceBuilder } from "../../hooks/useSentenceBuilder";
import { useChatChannel } from "../../hooks/useChatChannel";
import { ChatMessage, Frame, PredictionResult } from "../../types";

const CONFIDENCE_THRESHOLD = 70;

function readIntEnv(name: string, fallback: number): number {
  const raw = process.env[name];
  if (raw === undefined || raw === null || raw === "") {
    return fallback;
  }
  const parsed = Number.parseInt(raw, 10);
  if (!Number.isFinite(parsed) || parsed < 1) {
    return fallback;
  }
  return parsed;
}

const RECORDING_MAX_FRAMES = readIntEnv(
  "NEXT_PUBLIC_RECORDING_MAX_FRAMES",
  24
);
const PREDICT_STRIDE_FRAMES = readIntEnv(
  "NEXT_PUBLIC_SEND_STRIDE",
  4
);

function detectTasksHarness(): boolean {
  if (typeof window === "undefined") return false;
  try {
    const params = new URLSearchParams(window.location.search);
    return params.get("mp") === "tasks";
  } catch (e) {
    return false;
  }
}

export default function PacientePage() {
  console.log("[Render] PacientePage");
  const [mode, setMode] = useState<"predict" | "capture">("predict");
  const modeRef = useRef(mode);
  const [useTasksHarness, setUseTasksHarness] = useState(false);

  useEffect(() => {
    setUseTasksHarness(detectTasksHarness());
  }, []);

  const { chatHistory, sendMessage, clearHistory } = useChatChannel();

  const recordedFrames = useRef<Frame[]>([]);
  const framesSinceLastPredictRef = useRef(0);
  const captureHandlerRef = useRef<((f: Frame) => void) | null>(null);

  useEffect(() => {
    modeRef.current = mode;
  }, [mode]);

  // --- Sentence building from predictions ---
  const handleNewPatientMessage = useCallback((msg: ChatMessage) => {
    sendMessage(msg);
  }, [sendMessage]);

  const {
    transcript,
    isProcessingSentence,
    addWord,
    processSentence,
    onFrameTick,
    handleIdlePrediction,
  } = useSentenceBuilder(handleNewPatientMessage);

  const handleNewPrediction = useCallback(
    (data: PredictionResult) => {
      if (data.top3) {
        data.top3.forEach((item, index) => {
          const signEl = document.getElementById(`pred-sign-${index}`);
          if (signEl) signEl.innerText = item.sign;
          const confEl = document.getElementById(`pred-conf-${index}`);
          if (confEl) confEl.innerText = `${item.confidence.toFixed(1)}%`;
          const barEl = document.getElementById(`pred-bar-${index}`);
          if (barEl) barEl.style.width = `${item.confidence}%`;
        });
      }

      if (data.sign !== "idle") {
        if (data.confidence >= CONFIDENCE_THRESHOLD) {
          addWord(data.sign);
        }
      } else {
        handleIdlePrediction();
      }
    },
    [addWord, handleIdlePrediction]
  );

  // --- WebSocket for sign predictions ---
  const { wsStatus, sendFrames } = useSignWebSocket({ onMessage: handleNewPrediction });

  // --- MediaPipe frame handling ---
  const handleFrame = useCallback(
    (frameData: Frame) => {
      if (modeRef.current === "capture") {
        if (captureHandlerRef.current) {
          captureHandlerRef.current(frameData);
        }
        return;
      }

      recordedFrames.current.push(frameData);
      if (recordedFrames.current.length > RECORDING_MAX_FRAMES) {
        recordedFrames.current.shift();
      }

      framesSinceLastPredictRef.current++;
      if (
        recordedFrames.current.length >= 20 &&
        framesSinceLastPredictRef.current >= PREDICT_STRIDE_FRAMES
      ) {
        sendFrames([...recordedFrames.current]);
        framesSinceLastPredictRef.current = 0;
      }

      onFrameTick(frameData);
    },
    [sendFrames, onFrameTick]
  );

  const { videoRef, canvasRef, status, setStatus, stream } = useTasksHarness
    ? useMediaPipeTasks({
        onFrame: handleFrame,
        drawLandmarksOnCanvas: true,
      })
    : useMediaPipe({
        onFrame: handleFrame,
        drawLandmarksOnCanvas: true,
      });

  return (
    <>
      {mode === "capture" ? (
        <CaptureMode
          videoRef={videoRef}
          canvasRef={canvasRef}
          status={status}
          setStatus={setStatus}
          setMode={setMode}
          captureHandlerRef={captureHandlerRef}
        />
      ) : (
        <main className="min-h-screen bg-slate-50 flex flex-col">
          <Header />

        <div className="flex-1 flex flex-col p-8 pb-20 max-w-[1600px] mx-auto w-full">
          <div className="mb-8">
            <h2 className="text-2xl font-bold text-slate-800">
              Estación del Paciente
            </h2>
            <p className="text-slate-500 font-medium">
              El sistema traduce las señas del paciente a texto en tiempo real y
              muestra la conversación completa.
            </p>
          </div>

          <div className="flex flex-col lg:flex-row gap-6 h-full min-h-[600px]">
            {/* Camera panel */}
            <div className="flex-1 bg-white rounded-[2rem] shadow-sm border border-slate-200 p-6 flex-col flex">
              <div className="flex items-center gap-3 mb-6">
                <Camera className="text-indigo-600" size={24} />
                <h3 className="text-xl font-bold text-slate-800">
                  Captando señas...
                </h3>
              </div>

              <div className="flex-1 bg-slate-900 rounded-3xl overflow-hidden relative border-4 border-slate-800 shadow-inner flex flex-col items-center justify-center min-h-[400px]">
                <div className="absolute top-4 left-4 z-20 flex items-center gap-2 bg-slate-900/90 border border-slate-700 px-3 py-1.5 rounded-full">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
                  <span className="text-xs text-slate-100 font-semibold tracking-wide">
                    EN VIVO · Visión por computadora
                  </span>
                </div>

                <video
                  ref={videoRef}
                  className="absolute inset-0 w-full h-full object-cover"
                  playsInline
                  muted
                />
                <canvas
                  ref={canvasRef}
                  className="absolute inset-0 w-full h-full object-cover z-10"
                />

                {status === "loading" && (
                  <div className="z-20 flex flex-col items-center gap-4">
                    <Camera size={48} className="text-slate-700" />
                    <span className="text-slate-400 font-medium">
                      Activando cámara...
                    </span>
                  </div>
                )}

                {(transcript || isProcessingSentence) && (
                  <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-30 bg-slate-900/95 border border-slate-700 px-6 py-3 rounded-full shadow-lg flex items-center gap-3 max-w-[80%]">
                    {isProcessingSentence ? (
                      <div className="flex items-center gap-3">
                        <div className="w-4 h-4 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin" />
                        <span className="text-sm font-medium text-indigo-300">
                          Generando respuesta de IA...
                        </span>
                      </div>
                    ) : (
                      <span className="text-sm font-medium text-white truncate">
                        {transcript}
                      </span>
                    )}
                  </div>
                )}
              </div>

              <TopPredictions />
            </div>

            {/* Right panel - Chat History */}
            <div className="flex-1 flex flex-col gap-6 min-h-0">
              <div className="flex-1 bg-white rounded-[2rem] shadow-sm border border-slate-200 p-6 flex flex-col min-h-0 overflow-hidden">
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center gap-3">
                    <MonitorPlay className="text-indigo-600" size={24} />
                    <h3 className="text-xl font-bold text-slate-800">
                      Conversación:
                    </h3>
                  </div>
                </div>

                <div className="flex-1 bg-slate-100/50 border border-slate-200 rounded-3xl p-6 overflow-y-auto flex flex-col gap-6">
                  {chatHistory.length === 0 ? (
                    <div className="m-auto text-slate-400 flex flex-col items-center">
                      <p>La conversación aparecerá aquí</p>
                    </div>
                  ) : (
                    chatHistory.map((msg) => (
                      <ChatBubble key={msg.id} msg={msg} />
                    ))
                  )}
                </div>

                <div className="mt-4 flex justify-start">
                  <button
                    onClick={clearHistory}
                    className="flex items-center gap-2 px-4 py-2 text-slate-500 hover:text-red-500 hover:bg-red-50 rounded-xl transition-colors text-sm font-medium"
                  >
                    <Trash2 size={16} /> Limpiar Historial
                  </button>
                  <button
                    onClick={() => setMode("capture")}
                    className="ml-auto flex items-center gap-2 px-4 py-2 text-slate-400 hover:text-slate-600 text-sm"
                  >
                    <Settings size={16} /> Ajustes (Modo Captura)
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
      )}
    </>
  );
}
