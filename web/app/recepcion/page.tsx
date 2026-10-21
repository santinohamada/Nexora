"use client";

import { useCallback } from "react";
import { MonitorPlay, CheckCircle } from "lucide-react";
import { Header } from "../../components/layout/Header";
import { ChatBubble } from "../../components/chat/ChatBubble";
import { ReceptionControls } from "../../components/reception/ReceptionControls";
import { useChatChannel } from "../../hooks/useChatChannel";
import { sendAudit } from "../../lib/audit";

export default function RecepcionPage() {
  console.log("[Render] RecepcionPage");
  
  const { chatHistory, sendMessage, markReported, clearHistory } = useChatChannel();

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
    <main className="min-h-screen bg-slate-50 flex flex-col">
      <Header />

      <div className="flex-1 flex flex-col p-8 pb-20 max-w-[1600px] mx-auto w-full">
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-slate-800">
            Estación de Recepción / Enfermería
          </h2>
          <p className="text-slate-500 font-medium">
            Monitor de conversación con el paciente y envío de respuestas en texto.
          </p>
        </div>

        <div className="flex flex-col lg:flex-row gap-6 h-full min-h-[600px]">
          {/* Reception history panel */}
          <div className="flex-1 bg-slate-50 border border-slate-200 rounded-[2rem] overflow-hidden flex flex-col">
            <div className="bg-white p-6 border-b border-slate-200 flex items-center justify-between gap-4">
              <h3 className="text-xl font-bold text-slate-800">
                Historial del Paciente
              </h3>
              <button
                type="button"
                onClick={handleFinalizeAttention}
                className="flex items-center gap-2 px-4 py-2 bg-[#1e448a] hover:bg-[#15346b] text-white text-sm font-semibold rounded-xl transition-colors"
              >
                <CheckCircle size={16} /> Finalizar atención
              </button>
            </div>
            <div className="flex-1 p-6 overflow-y-auto space-y-6 bg-slate-50/50">
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
          </div>

          {/* Right panel - Controls */}
          <div className="flex-1 flex flex-col gap-6">
            <ReceptionControls onSend={handleSendReception} />
          </div>
        </div>
      </div>
    </main>
  );
}
