"use client";

import { useEffect, useRef, useCallback } from "react";
import { Camera, MonitorPlay, Trash2 } from "lucide-react";
import { Header } from "../../../components/layout/Header";
import { TopPredictions } from "../../../components/camera/TopPredictions";
import { SkeletonToggle } from "../../../components/camera/SkeletonToggle";
import { ChatBubble } from "../../../components/chat/ChatBubble";
import { useSignWebSocket } from "../../../hooks/useSignWebSocket";
import { useSentenceBuilder } from "../../../hooks/useSentenceBuilder";
import { useStation } from "../../../components/stations/StationProvider";
import { ChatMessage, Frame, PredictionResult } from "../../../types";

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
  45
);
const PREDICT_STRIDE_FRAMES = readIntEnv(
  "NEXT_PUBLIC_SEND_STRIDE",
  8
);

export default function PacientePage() {
  console.log("[Render] PacientePage");

  const {
    showConsentDialog,
    chatHistory,
    sendMessage,
    markReported,
    clearHistory,
    showSkeleton,
    setShowSkeleton,
    videoRef,
    canvasRef,
    cameraStatus: status,
    cameraError,
    setFrameHandler,
  } = useStation();

  // Keep the latest message in view once the chat overflows its fixed-height panel
  const chatScrollRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = chatScrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [chatHistory.length]);

  const recordedFrames = useRef<Frame[]>([]);
  const framesSinceLastPredictRef = useRef(0);

  // --- Sentence building from predictions ---
  const handleNewPatientMessage = useCallback((msg: ChatMessage) => {
    sendMessage(msg);
  }, [sendMessage]);

  const {
    transcript,
    isProcessingSentence,
    addWord,
    processSentence,
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

      if (data.sign === "idle") {
        // Hands down (or nobody in frame) ends the sentence; pauses between signs keep the hands up.
        if (data.confidence >= CONFIDENCE_THRESHOLD) processSentence();
      } else {
        const idleDominant = (data.top3 ?? []).some(
          (item) => item.sign === "idle" && item.confidence > 50
        );
        if (!idleDominant && data.confidence >= CONFIDENCE_THRESHOLD) {
          addWord(data.sign);
        }
      }
    },
    [addWord, processSentence]
  );

  // --- WebSocket for sign predictions ---
  const { sendFrames } = useSignWebSocket({ onMessage: handleNewPrediction });

  const handleFrame = useCallback(
    (frameData: Frame) => {
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
    },
    [sendFrames]
  );

  useEffect(() => {
    setFrameHandler(handleFrame);
    return () => setFrameHandler(null);
  }, [handleFrame, setFrameHandler]);

  return (
      <main className="min-h-screen bg-slate-50 flex flex-col" inert={showConsentDialog}>
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

          {/* Fixed height on desktop: a growing chat scrolls inside its panel instead of stretching the camera */}
          <div className="flex flex-col lg:flex-row gap-6 min-h-[600px] lg:h-[600px]">
            {/* Camera panel */}
            <div className="flex-1 bg-white rounded-[2rem] shadow-sm border border-slate-200 p-6 flex-col flex">
              <div className="flex items-center gap-3 mb-6">
                <Camera className="text-indigo-600" size={24} />
                <h3 className="text-xl font-bold text-slate-800">
                  Captando señas...
                </h3>
              </div>

              <div className="flex-1 bg-slate-900 rounded-3xl overflow-hidden relative border-4 border-slate-800 shadow-inner flex flex-col items-center justify-center min-h-[400px]">
                {status !== "error" && (
                  <div className="absolute top-4 left-4 z-20 flex items-center gap-2 bg-slate-900/90 border border-slate-700 px-3 py-1.5 rounded-full">
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
                    <span className="text-xs text-slate-100 font-semibold tracking-wide">
                      EN VIVO · Visión por computadora
                    </span>
                  </div>
                )}

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

                {status === "error" && (
                  <div role="alert" className="z-20 flex flex-col items-center gap-4 px-6 text-center">
                    <Camera size={48} className="text-slate-500" />
                    <span className="text-red-300 font-medium">
                      {cameraError ?? "No se pudo acceder a la cámara."}
                    </span>
                  </div>
                )}

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

              <SkeletonToggle checked={showSkeleton} onChange={setShowSkeleton} />

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

                <div ref={chatScrollRef} className="flex-1 bg-slate-100/50 border border-slate-200 rounded-3xl p-6 overflow-y-auto flex flex-col gap-6">
                  {chatHistory.length === 0 ? (
                    <div className="m-auto text-slate-600 flex flex-col items-center">
                      <p>La conversación aparecerá aquí</p>
                    </div>
                  ) : (
                    chatHistory.map((msg) => (
                      <ChatBubble key={msg.id} msg={msg} onReported={markReported} />
                    ))
                  )}
                </div>

                <div className="mt-4 flex justify-start">
                  <button
                    onClick={clearHistory}
                    className="flex items-center gap-2 px-4 py-2 text-slate-600 hover:text-red-600 hover:bg-slate-100 rounded-xl transition-colors text-sm font-medium"
                  >
                    <Trash2 size={16} /> Limpiar Historial
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
  );
}
