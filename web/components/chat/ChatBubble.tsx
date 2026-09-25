import { memo, useState } from "react";
import { usePathname } from "next/navigation";
import { Flag, Check } from "lucide-react";
import { ChatMessage } from "../../types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type ReportState = "idle" | "sending" | "reported" | "error";

export const ChatBubble = memo(function ChatBubble({
  msg,
}: {
  msg: ChatMessage;
}) {
  console.log("[Render] ChatBubble");
  const isPatient = msg.role === "PACIENTE";
  const pathname = usePathname();
  const station = pathname === "/recepcion" ? "recepcion" : "paciente";
  const [reportState, setReportState] = useState<ReportState>("idle");

  const handleReport = async () => {
    setReportState("sending");
    try {
      const res = await fetch(`${API_URL}/report`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: msg.text,
          station,
          ...(msg.words && msg.words.length > 0 ? { words: msg.words } : {}),
        }),
      });
      if (!res.ok) throw new Error("report failed");
      setReportState("reported");
    } catch {
      setReportState("error");
    }
  };

  return (
    <div
      className={`flex flex-col max-w-[85%] ${isPatient ? "self-start" : "self-end items-end"}`}
    >
      <div
        className={`p-4 rounded-3xl relative shadow-sm ${
          isPatient
            ? "bg-white text-slate-800 rounded-tl-none border border-slate-200"
            : "bg-[#1e448a] text-white rounded-tr-none"
        }`}
      >
        <div
          className={`text-[10px] font-bold uppercase tracking-wider mb-1 ${isPatient ? "text-teal-500" : "text-blue-200"}`}
        >
          {msg.role}
        </div>
        <p className="text-[15px] leading-relaxed pb-4">{msg.text}</p>
        {isPatient && (
          <div className="absolute bottom-3 left-4">
            {reportState === "reported" ? (
              <span className="flex items-center gap-1 text-[10px] font-semibold text-emerald-600">
                <Check size={12} /> Reportado
              </span>
            ) : (
              <button
                type="button"
                onClick={handleReport}
                disabled={reportState === "sending"}
                aria-label="Reportar traducción incorrecta o ambigua"
                className="flex items-center gap-1 text-[10px] font-medium text-slate-400 hover:text-red-500 disabled:opacity-50 disabled:hover:text-slate-400 transition-colors"
              >
                <Flag size={12} />
                {reportState === "sending" ? "Enviando..." : "Reportar traducción"}
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
      {reportState === "error" && (
        <p className="text-[10px] text-red-500 mt-1 px-1">
          No se pudo enviar el reporte. Probá de nuevo.
        </p>
      )}
    </div>
  );
});
