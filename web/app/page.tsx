"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { Camera, MonitorPlay, Trash2, Settings } from "lucide-react";
import { Header } from "../components/layout/Header";
import { Footer } from "../components/layout/Footer";
import { TopPredictions } from "../components/camera/TopPredictions";
import { ChatBubble } from "../components/chat/ChatBubble";
import { ReceptionControls } from "../components/reception/ReceptionControls";
import { CaptureMode } from "../components/capture/CaptureMode";
import { useMediaPipe } from "../hooks/useMediaPipe";
import { useSignWebSocket } from "../hooks/useSignWebSocket";
import { useSentenceBuilder } from "../hooks/useSentenceBuilder";
import { ChatMessage, Frame } from "../types";

const RECORDING_MAX_FRAMES = 45;
const CONFIDENCE_THRESHOLD = 70;

export default function HomePage() {
  const [mode, setMode] = useState<"predict" | "capture">("predict");
  const modeRef = useRef(mode);
  const [view, setView] = useState<"paciente" | "recepcion">("paciente");
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);

  const recordedFrames = useRef<Frame[]>([]);
  const framesSinceLastPredictRef = useRef(0);

  useEffect(() => {
    modeRef.current = mode;
  }, [mode]);

  // --- WebSocket for sign predictions ---
  const { prediction, wsStatus, sendFrames } = useSignWebSocket();

  // --- Sentence building from predictions ---
  const handleNewPatientMessage = useCallback((msg: ChatMessage) => {
    setChatHistory((prev) => [...prev, msg]);
  }, []);

  const { transcript, isProcessingSentence, addWord, processSentence } =
    useSentenceBuilder(handleNewPatientMessage);

  const idleTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Process confident predictions into transcript words and handle idle timeout
  useEffect(() => {
    if (!prediction) return;
    
    if (prediction.sign !== "idle") {
      // Clear idle timeout when a real sign is detected
      if (idleTimerRef.current) {
        clearTimeout(idleTimerRef.current);
        idleTimerRef.current = null;
      }
      
      if (prediction.confidence >= CONFIDENCE_THRESHOLD) {
        addWord(prediction.sign);
      }
    } else {
      // It's idle. If we have a transcript and no timer is running, wait 2s to process
      if (transcript && !isProcessingSentence && !idleTimerRef.current) {
        idleTimerRef.current = setTimeout(() => {
          processSentence();
          idleTimerRef.current = null;
        }, 2000);
      }
    }
  }, [prediction, addWord, processSentence, transcript, isProcessingSentence]);

  // --- MediaPipe frame handling ---
  const handleFrame = useCallback(
    (frameData: Frame) => {
      if (modeRef.current === "capture") return;

      recordedFrames.current.push(frameData);
      if (recordedFrames.current.length > RECORDING_MAX_FRAMES) {
        recordedFrames.current.shift();
      }

      framesSinceLastPredictRef.current++;
      if (
        recordedFrames.current.length === RECORDING_MAX_FRAMES &&
        framesSinceLastPredictRef.current >= 10
      ) {
        sendFrames([...recordedFrames.current]);
        framesSinceLastPredictRef.current = 0;
      }
    },
    [sendFrames]
  );

  const { videoRef, canvasRef, status, setStatus } = useMediaPipe({
    onFrame: handleFrame,
    drawLandmarksOnCanvas: mode === "capture",
  });

  // --- Event handlers ---
  const handleSendReception = useCallback((text: string) => {
    setChatHistory((prev) => [
      ...prev,
      {
        id: Date.now(),
        role: "RECEPCIONISTA" as const,
        text,
        time: new Date().toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        }),
      },
    ]);
  }, []);

  const handleClearHistory = useCallback(() => {
    setChatHistory([]);
  }, []);

  // --- Render ---
  if (mode === "capture") {
    return (
      <>
        {/* Video must stay in DOM — MediaPipe Camera holds a direct reference */}
        <video
          ref={videoRef}
          className="fixed top-0 left-0 w-px h-px opacity-0 pointer-events-none"
          playsInline
          muted
        />
        <CaptureMode
          canvasRef={canvasRef}
          status={status}
          setStatus={setStatus}
          setMode={setMode}
        />
      </>
    );
  }

  return (
    <>
      {/* Video must stay in DOM — MediaPipe Camera holds a direct reference */}
      <video
        ref={videoRef}
        className="fixed top-0 left-0 w-px h-px opacity-0 pointer-events-none"
        playsInline
        muted
      />
      <main className="min-h-screen bg-slate-50 flex flex-col">
        <Header view={view} setView={setView} />

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
          <div
            className={`flex-1 bg-white rounded-[2rem] shadow-sm border border-slate-200 p-6 flex-col ${
              view === "paciente" ? "flex" : "hidden"
            }`}
          >
            <div className="flex items-center gap-3 mb-6">
              <Camera className="text-indigo-600" size={24} />
              <h3 className="text-xl font-bold text-slate-800">
                Captando señas...
              </h3>
            </div>

            <div className="flex-1 bg-slate-900 rounded-3xl overflow-hidden relative border-4 border-slate-800 shadow-inner flex flex-col items-center justify-center min-h-[400px]">
              <div className="absolute top-4 left-4 z-20 flex items-center gap-2 bg-slate-950/60 backdrop-blur-md border border-white/10 px-3 py-1.5 rounded-full">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse shadow-[0_0_8px_rgba(52,211,153,0.8)]" />
                <span className="text-xs text-slate-100 font-semibold tracking-wide">
                  EN VIVO · Visión por computadora
                </span>
              </div>


              <canvas
                ref={canvasRef}
                className="absolute inset-0 w-full h-full object-cover z-10 opacity-80"
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
                <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-30 bg-slate-900/80 backdrop-blur-xl border border-white/10 px-6 py-3 rounded-full shadow-2xl flex items-center gap-3 max-w-[80%]">
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

            <TopPredictions prediction={prediction} />
          </div>

          {/* Reception history panel */}
          <div
            className={`flex-1 bg-slate-50 border border-slate-200 rounded-[2rem] overflow-hidden flex-col ${
              view === "recepcion" ? "flex" : "hidden"
            }`}
          >
            <div className="bg-white p-6 border-b border-slate-200">
              <h3 className="text-xl font-bold text-slate-800">
                Historial del Paciente
              </h3>
            </div>
            <div className="flex-1 p-6 overflow-y-auto space-y-6 bg-slate-50/50">
              {chatHistory.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-slate-400">
                  <MonitorPlay size={48} className="mb-4 opacity-50" />
                  <p>No hay mensajes en la conversación.</p>
                </div>
              ) : (
                chatHistory.map((msg) => (
                  <ChatBubble key={msg.id} msg={msg} />
                ))
              )}
            </div>
          </div>

          {/* Right panel */}
          <div className="flex-1 flex flex-col gap-6">
            {view === "paciente" ? (
              <div className="flex-1 bg-white rounded-[2rem] shadow-sm border border-slate-200 p-6 flex flex-col">
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
                    onClick={handleClearHistory}
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
            ) : (
              <ReceptionControls onSend={handleSendReception} />
            )}
          </div>
        </div>
      </div>

        <Footer prediction={prediction} wsStatus={wsStatus} />
      </main>
    </>
  );
}
