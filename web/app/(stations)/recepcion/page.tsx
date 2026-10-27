"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Camera, MonitorPlay, CheckCircle } from "lucide-react";
import { Header } from "../../../components/layout/Header";
import { ChatBubble } from "../../../components/chat/ChatBubble";
import { SignCaption, SkeletonToggle } from "../../../components/camera/SkeletonToggle";
import { ReceptionControls } from "../../../components/reception/ReceptionControls";
import { ReceptionChatHeader } from "../../../components/reception/ReceptionChatHeader";
import { useStation } from "../../../components/stations/StationProvider";
import { sendAudit } from "../../../lib/audit";

export default function RecepcionPage() {
  console.log("[Render] RecepcionPage");

  const {
    chatHistory,
    sendMessage,
    markReported,
    deleteMessage,
    clearHistory,
    stream,
    showConsentDialog,
    videoRef,
    canvasRef,
    showSkeleton,
    setShowSkeleton,
    showWords,
    setShowWords,
    transcript,
    isProcessingSentence,
  } = useStation();
  const [remoteFrame, setRemoteFrame] = useState<string | null>(null);
  const chatScrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = chatScrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [chatHistory.length]);

  useEffect(() => {
    if (stream) return;
    const bc = new BroadcastChannel("nexora-camera");
    bc.onmessage = (event: MessageEvent<string>) => {
      if (typeof event.data === "string") setRemoteFrame(event.data);
    };
    return () => bc.close();
  }, [stream]);

  const handleSendReception = useCallback((text: string) => {
    sendMessage({
      id: Date.now(),
      role: "RECEPCIONISTA",
      text,
      time: new Date().toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      }),
    });
    sendAudit({ type: "reply_sent", station: "recepcion" });
  }, [sendMessage]);

  const handleFinalizeAttention = useCallback(() => {
    if (!chatHistory.length) return;
    clearHistory();
    sendAudit({ type: "fin_atencion", station: "recepcion" });
  }, [chatHistory.length, clearHistory]);

  return (
    <main className="h-screen bg-slate-50 flex flex-col overflow-hidden" inert={showConsentDialog}>
      <Header />

      <div className="flex-1 min-h-0 flex flex-col p-4 lg:p-6 max-w-[1600px] mx-auto w-full">
        <div className="flex flex-col lg:flex-row gap-4 lg:gap-6 flex-1 min-h-0 items-stretch">
          <div className="flex-1 min-w-0 min-h-0 bg-white border border-slate-200 rounded-[2rem] overflow-hidden flex flex-col order-1">
            <div className="bg-white px-4 lg:px-6 py-3 border-b border-slate-200 flex items-center justify-between gap-4 shrink-0">
              <ReceptionChatHeader />
              <button
                type="button"
                onClick={handleFinalizeAttention}
                className="flex items-center gap-2 px-4 py-2 bg-[#1e448a] hover:bg-[#15346b] text-white text-sm font-semibold rounded-xl transition-colors"
              >
                <CheckCircle size={16} /> Finalizar atención
              </button>
            </div>
            <div
              ref={chatScrollRef}
              className="flex-1 min-h-0 p-4 overflow-y-auto space-y-1.5 bg-slate-50/50"
            >
              {chatHistory.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-slate-600">
                  <MonitorPlay size={48} className="mb-4 opacity-50" />
                  <p>No hay mensajes en la conversación.</p>
                </div>
              ) : (
                chatHistory.map((msg) => (
                  <ChatBubble key={msg.id} msg={msg} onReported={markReported} onDelete={deleteMessage} />
                ))
              )}
            </div>
            <div className="shrink-0 border-t border-slate-200 p-3">
              <ReceptionControls onSend={handleSendReception} />
            </div>
          </div>

          <div className="w-full lg:w-[22rem] xl:w-[26rem] shrink-0 flex flex-col self-start order-2">
            <div className="bg-slate-900 rounded-[2rem] overflow-hidden flex flex-col border border-slate-200">
              <div className="bg-white px-4 py-2.5 border-b border-slate-200 shrink-0">
                <h3 className="text-base font-bold text-slate-800">Cámara del paciente</h3>
              </div>
              <div className="relative aspect-video w-full flex items-center justify-center bg-slate-950">
                <video
                  ref={videoRef}
                  className="absolute inset-0 w-full h-full object-contain"
                  playsInline
                  muted
                />
                <canvas
                  ref={canvasRef}
                  className="absolute inset-0 w-full h-full object-contain z-10 pointer-events-none"
                />
                {!stream && remoteFrame && (
                  <img
                    src={remoteFrame}
                    alt="Cámara del paciente"
                    className="absolute inset-0 w-full h-full object-contain"
                  />
                )}
                {!stream && !remoteFrame && (
                  <div className="relative z-20 flex flex-col items-center gap-2 text-slate-400">
                    <Camera size={32} />
                    <p className="text-sm text-center px-2">Esperando la cámara del paciente</p>
                  </div>
                )}
                <SignCaption show={showWords} transcript={transcript} busy={isProcessingSentence} />
              </div>
            </div>
            <SkeletonToggle checked={showSkeleton} onChange={setShowSkeleton} label="Mostrar esqueleto" />
            <SkeletonToggle checked={showWords} onChange={setShowWords} label="Mostrar palabras" />
          </div>
        </div>
      </div>
    </main>
  );
}
