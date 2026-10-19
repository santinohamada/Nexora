import { memo, useState } from "react";
import { usePathname } from "next/navigation";
import { Flag, AlertTriangle } from "lucide-react";
import { ChatMessage } from "../../types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type SendState = "idle" | "sending" | "error";

export const ChatBubble = memo(function ChatBubble({
  msg,
  onReported,
}: {
  msg: ChatMessage;
  onReported?: (id: number) => void;
}) {
  console.log("[Render] ChatBubble");
  const isPatient = msg.role === "PACIENTE";
  const pathname = usePathname();
  const station = pathname === "/recepcion" ? "recepcion" : "paciente";
  const [sendState, setSendState] = useState<SendState>("idle");
  const isReported = Boolean(msg.reported);

  const handleReport = async () => {
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
    }
  };

  const reportedNotice =
    station === "paciente"
      ? "Traducción reportada. Repetí la seña para enviar el mensaje de nuevo."
      : "Traducción reportada como incorrecta. No la tomes como válida: el paciente va a repetir la seña.";

  return (
    <div
      className={`flex flex-col max-w-[85%] ${isPatient ? "self-start" : "self-end items-end"}`}
    >
      <div
        className={`p-4 rounded-3xl relative shadow-sm transition-colors ${
          isPatient
            ? isReported
              ? "bg-amber-50 text-slate-500 rounded-tl-none border border-amber-300"
              : "bg-white text-slate-800 rounded-tl-none border border-slate-200"
            : "bg-[#1e448a] text-white rounded-tr-none"
        }`}
      >
        <div
          className={`text-[10px] font-bold uppercase tracking-wider mb-1 ${isPatient ? "text-teal-500" : "text-blue-200"}`}
        >
          {msg.role}
        </div>
        <p
          className={`text-[15px] leading-relaxed pb-4 ${isReported ? "line-through decoration-amber-400/70" : ""}`}
        >
          {msg.text}
        </p>
        {isPatient && (
          <div className="absolute bottom-3 left-4">
            {isReported ? (
              <span className="flex items-center gap-1 text-[10px] font-semibold text-amber-700">
                <AlertTriangle size={12} /> Traducción reportada
              </span>
            ) : (
              <button
                type="button"
                onClick={handleReport}
                disabled={sendState === "sending"}
                aria-label="Reportar traducción incorrecta o ambigua"
                className="flex items-center gap-1 text-[10px] font-medium text-slate-400 hover:text-red-500 disabled:opacity-50 disabled:hover:text-slate-400 transition-colors"
              >
                <Flag size={12} />
                {sendState === "sending" ? "Enviando..." : "Reportar traducción"}
              </button>
            )}
          </div>
        )}
        <span
          className={`absolute bottom-3 right-4 text-[10px] ${isPatient ? "text-slate-400" : "text-blue-300"}`}
        >
          {msg.time}
        </span>
      </div>
      {isPatient && isReported && (
        <p role="status" className="text-[11px] text-amber-700 mt-1 px-1 max-w-sm">
          {reportedNotice}
        </p>
      )}
      {sendState === "error" && (
        <p role="alert" className="text-[10px] text-red-500 mt-1 px-1">
          No se pudo enviar el reporte. Probá de nuevo.
        </p>
      )}
    </div>
  );
});
