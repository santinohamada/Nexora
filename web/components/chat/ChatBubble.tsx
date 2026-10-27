import { memo, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import { Flag, AlertTriangle, Trash2 } from "lucide-react";
import { ChatMessage } from "../../types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type SendState = "idle" | "sending" | "error";

export const ChatBubble = memo(function ChatBubble({
  msg,
  onReported,
  onDelete,
}: {
  msg: ChatMessage;
  onReported?: (id: number) => void;
  onDelete?: (id: number) => void;
}) {
  console.log("[Render] ChatBubble");
  const isPatient = msg.role === "PACIENTE";
  const pathname = usePathname();
  const station = pathname === "/recepcion" ? "recepcion" : "paciente";
  const isOwn = station === "recepcion" ? !isPatient : isPatient;
  const [sendState, setSendState] = useState<SendState>("idle");
  const isReported = Boolean(msg.reported);

  const inFlight = useRef(false);

  const handleReport = async () => {
    if (inFlight.current || isReported) return;
    inFlight.current = true;
    setSendState("sending");
    try {
      const res = await fetch(`${API_URL}/report`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: msg.text,
          station,
          message_id: msg.id,
          ...(msg.words && msg.words.length > 0 ? { words: msg.words } : {}),
        }),
      });
      if (!res.ok) throw new Error("report failed");
      setSendState("idle");
      onReported?.(msg.id);
    } catch {
      setSendState("error");
    } finally {
      inFlight.current = false;
    }
  };

  const reportedNotice =
    station === "paciente"
      ? "Traducción reportada. Repetí la seña para enviar el mensaje de nuevo."
      : "Traducción reportada como incorrecta. No la tomes como válida: el paciente va a repetir la seña.";

  const bubbleClass = isOwn
    ? "bg-[#1e448a] text-white rounded-2xl rounded-br-md"
    : isReported
      ? "bg-amber-50 text-slate-600 rounded-2xl rounded-bl-md border border-amber-300"
      : "bg-white text-slate-800 rounded-2xl rounded-bl-md border border-slate-200/80";

  const canDelete = Boolean(onDelete) && station === "recepcion" && isOwn && !isPatient;

  return (
    <div className={`flex w-full min-w-0 ${isOwn ? "justify-end" : "justify-start"}`}>
      <div
        className={`flex min-w-0 max-w-[min(78%,18rem)] gap-1 ${isOwn ? "flex-row items-end" : "flex-col"}`}
      >
        {canDelete && (
          <button
            type="button"
            onClick={() => onDelete?.(msg.id)}
            aria-label="Eliminar mensaje"
            className="shrink-0 p-1 mb-0.5 text-slate-400 hover:text-red-600 transition-colors rounded-md"
          >
            <Trash2 size={15} />
          </button>
        )}
        <div className="flex flex-col min-w-0 flex-1">
        <div className={`px-2.5 py-1.5 shadow-sm ${bubbleClass}`}>
          <div
            className={`inline-flex flex-wrap items-end gap-x-1.5 max-w-full ${
              isOwn ? "justify-end" : "justify-start"
            }`}
          >
            <span
              data-chat-message
              className={`text-[13px] leading-snug break-words ${
                isReported ? "line-through decoration-amber-400/70" : ""
              }`}
            >
              {msg.text}
            </span>
            <span
              className={`text-[10px] leading-none shrink-0 translate-y-px ${
                isOwn ? "text-blue-200/85" : "text-slate-400"
              }`}
            >
              {msg.time}
            </span>
          </div>
        </div>
        {isPatient && (
          <div className={`mt-0.5 px-0.5 ${isOwn ? "text-right" : ""}`}>
            {isReported ? (
              <span className="flex items-center gap-1 text-[10px] font-medium text-amber-700">
                <AlertTriangle size={11} /> Traducción reportada
              </span>
            ) : (
              <button
                type="button"
                onClick={handleReport}
                disabled={sendState === "sending"}
                aria-label="Reportar traducción incorrecta o ambigua"
                className="flex items-center gap-1 text-[10px] font-medium text-slate-400 hover:text-red-500 disabled:opacity-50 transition-colors"
              >
                <Flag size={11} />
                {sendState === "sending" ? "Enviando..." : "Reportar traducción"}
              </button>
            )}
          </div>
        )}
        {isPatient && isReported && (
          <p role="status" className="text-[10px] text-amber-700 mt-0.5 px-0.5 max-w-sm leading-snug">
            {reportedNotice}
          </p>
        )}
        {sendState === "error" && (
          <p role="alert" className="text-[10px] text-red-500 mt-0.5 px-0.5">
            No se pudo enviar el reporte. Probá de nuevo.
          </p>
        )}
        </div>
      </div>
    </div>
  );
});
