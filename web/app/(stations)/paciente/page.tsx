"use client";

import { useEffect, useRef } from "react";
import { Camera, MonitorPlay, Trash2 } from "lucide-react";
import { Header } from "../../../components/layout/Header";
import { TopPredictions } from "../../../components/camera/TopPredictions";
import { SignCaption, SkeletonToggle } from "../../../components/camera/SkeletonToggle";
import { ChatBubble } from "../../../components/chat/ChatBubble";
import { useStation } from "../../../components/stations/StationProvider";

export default function PacientePage() {
  console.log("[Render] PacientePage");

  const {
    showConsentDialog,
    chatHistory,
    attendantName,
    markReported,
    clearHistory,
    showSkeleton,
    setShowSkeleton,
    showWords,
    setShowWords,
    videoRef,
    canvasRef,
    cameraStatus: status,
    cameraError,
    transcript,
    isProcessingSentence,
  } = useStation();

  const chatScrollRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = chatScrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [chatHistory.length]);

  return (
    <main className="h-screen bg-slate-50 flex flex-col overflow-hidden" inert={showConsentDialog}>
      <Header />

      <div className="flex-1 min-h-0 flex flex-col p-4 lg:p-6 max-w-[1600px] mx-auto w-full">
        <div className="flex flex-col lg:flex-row gap-4 lg:gap-6 flex-1 min-h-0">
          <div className="flex-1 flex flex-col min-h-0 min-w-0 order-1">
            <div className="flex-1 bg-white rounded-[2rem] shadow-sm border border-slate-200 p-4 lg:p-5 flex flex-col min-h-0 overflow-hidden">
              <div className="flex items-center gap-2 mb-3 shrink-0">
                <MonitorPlay className="text-indigo-600" size={22} />
                <h3 className="text-lg font-bold text-slate-800">
                  {attendantName ? `${attendantName} te está atendiendo` : "Conversación"}
                </h3>
              </div>

              <div
                ref={chatScrollRef}
                className="flex-1 min-h-0 bg-slate-100/50 border border-slate-200 rounded-3xl p-4 overflow-y-auto flex flex-col gap-1.5"
              >
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

              <div className="mt-3 flex justify-start shrink-0">
                <button
                  onClick={clearHistory}
                  className="flex items-center gap-2 px-4 py-2 text-slate-600 hover:text-red-600 hover:bg-slate-100 rounded-xl transition-colors text-sm font-medium"
                >
                  <Trash2 size={16} /> Limpiar Historial
                </button>
              </div>
            </div>
          </div>

          <div className="flex-1 min-h-0 min-w-0 flex flex-col order-2">
            <div className="flex-1 min-h-0 bg-white rounded-[2rem] shadow-sm border border-slate-200 p-4 lg:p-5 flex flex-col">
              <div className="flex items-center gap-2 mb-3 shrink-0">
                <Camera className="text-indigo-600" size={22} />
                <h3 className="text-lg font-bold text-slate-800">Captando señas...</h3>
              </div>

              <div className="flex-1 min-h-0 bg-slate-900 rounded-3xl overflow-hidden relative border-4 border-slate-800 shadow-inner flex flex-col items-center justify-center">
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
                    <span className="text-slate-400 font-medium">Activando cámara...</span>
                  </div>
                )}

                <SignCaption show={showWords} transcript={transcript} busy={isProcessingSentence} />
              </div>

              <SkeletonToggle checked={showSkeleton} onChange={setShowSkeleton} label="Mostrar esqueleto" />
              <SkeletonToggle checked={showWords} onChange={setShowWords} label="Mostrar palabras" />

              <TopPredictions />
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
