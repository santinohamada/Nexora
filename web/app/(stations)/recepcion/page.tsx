"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Camera, MonitorPlay, CheckCircle } from "lucide-react";
import { Header } from "../../../components/layout/Header";
import { ChatBubble } from "../../../components/chat/ChatBubble";
import { ReceptionControls } from "../../../components/reception/ReceptionControls";
import { useStation } from "../../../components/stations/StationProvider";
import { sendAudit } from "../../../lib/audit";

export default function RecepcionPage() {
  console.log("[Render] RecepcionPage");
  
  const { chatHistory, sendMessage, markReported, clearHistory, stream, showConsentDialog } = useStation();
  const previewRef = useRef<HTMLVideoElement>(null);
  const [remoteFrame, setRemoteFrame] = useState<string | null>(null);

  useEffect(() => {
    const el = previewRef.current;
    if (!el || !stream) return;
    if (el.srcObject !== stream) el.srcObject = stream;
    el.play().catch(() => {});
  }, [stream]);

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
    // CU-04 step 6 / CU-11: anonymous event, never the reply text
    sendAudit({ type: "reply_sent", station: "recepcion" });
  }, [sendMessage]);

  // CU-12: clears the conversation on both faces (CLEAR event) and audits the end of the attention
  const handleFinalizeAttention = useCallback(() => {
    if (!chatHistory.length) return; // nothing to close: no audit row for repeated clicks
    clearHistory();
    sendAudit({ type: "fin_atencion", station: "recepcion" });
  }, [chatHistory.length, clearHistory]);

  return (
    <main className="h-screen bg-slate-50 flex flex-col overflow-hidden" inert={showConsentDialog}>
      <Header />

      <div className="flex-1 min-h-0 flex flex-col p-8 max-w-[1600px] mx-auto w-full">
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-slate-800">
            Estación de Recepción / Enfermería
          </h2>
          <p className="text-slate-500 font-medium">
            Monitor de conversación con el paciente y envío de respuestas en texto.
          </p>
        </div>

        <div className="flex flex-col lg:flex-row gap-6 flex-1 min-h-0">
          <div className="w-full lg:w-[34rem] shrink-0 self-center bg-slate-900 rounded-[2rem] overflow-hidden flex flex-col border border-slate-200">
            <div className="bg-white px-4 py-2.5 border-b border-slate-200 shrink-0">
              <h3 className="text-base font-bold text-slate-800">Cámara del paciente</h3>
            </div>
            <div className="relative aspect-video w-full flex items-center justify-center bg-slate-950">
              <video
                ref={previewRef}
                className={`absolute inset-0 w-full h-full object-contain ${stream ? "" : "hidden"}`}
                playsInline
                muted
              />
              {!stream && remoteFrame && (
                <img
                  src={remoteFrame}
                  alt="Cámara del paciente"
                  className="absolute inset-0 w-full h-full object-contain"
                />
              )}
              {!stream && !remoteFrame && (
                <div className="flex flex-col items-center gap-2 text-slate-400">
                  <Camera size={32} />
                  <p className="text-sm text-center px-2">Esperando la cámara del paciente</p>
                </div>
              )}
            </div>
          </div>

          <div className="flex-1 min-w-0 min-h-0 bg-white border border-slate-200 rounded-[2rem] overflow-hidden flex flex-col">
            <div className="bg-white p-6 border-b border-slate-200 flex items-center justify-between gap-4 shrink-0">
              <h3 className="text-xl font-bold text-slate-800">Conversación</h3>
              <button
                type="button"
                onClick={handleFinalizeAttention}
                className="flex items-center gap-2 px-4 py-2 bg-[#1e448a] hover:bg-[#15346b] text-white text-sm font-semibold rounded-xl transition-colors"
              >
                <CheckCircle size={16} /> Finalizar atención
              </button>
            </div>
            <div className="flex-1 min-h-0 p-6 overflow-y-auto space-y-6 bg-slate-50/50">
              {chatHistory.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-slate-600">
                  <MonitorPlay size={48} className="mb-4 opacity-50" />
                  <p>No hay mensajes en la conversación.</p>
                </div>
              ) : (
                chatHistory.map((msg) => (
                  <ChatBubble key={msg.id} msg={msg} onReported={markReported} />
                ))
              )}
            </div>
            <div className="shrink-0 border-t border-slate-200 p-3">
              <ReceptionControls onSend={handleSendReception} />
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
