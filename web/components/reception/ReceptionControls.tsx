import { useState, memo } from "react";
import { Send, Mic } from "lucide-react";

export const ReceptionControls = memo(function ReceptionControls({
  onSend,
}: {
  onSend: (text: string) => void;
}) {
  const [receptionText, setReceptionText] = useState("");

  const handleSend = () => {
    if (!receptionText.trim()) return;
    onSend(receptionText.trim());
    setReceptionText("");
  };

  return (
    <div className="flex-1 flex flex-col gap-6">
      <div className="bg-white rounded-[2rem] shadow-sm border border-slate-200 p-6 flex flex-col">
        <textarea
          value={receptionText}
          onChange={(e) => setReceptionText(e.target.value)}
          placeholder="Escribir..."
          className="w-full h-32 bg-slate-100 border border-slate-200 rounded-2xl p-4 text-slate-800 outline-none focus:ring-2 focus:ring-indigo-500 resize-none mb-4"
        />
        <button
          onClick={handleSend}
          disabled={!receptionText.trim()}
          className="w-full py-4 bg-[#1e448a] hover:bg-[#15346b] disabled:opacity-50 text-white font-semibold rounded-2xl flex justify-center items-center gap-2 transition-colors shadow-md"
        >
          <Send size={18} /> Enviar
        </button>
      </div>

      <div className="flex-1 bg-white rounded-[2rem] shadow-sm border border-slate-200 p-6 flex flex-col">
        <h3 className="text-xl font-bold text-slate-800 mb-6">
          Respuesta por voz:
        </h3>
        <div className="flex-1 flex items-center justify-center">
          <div className="flex items-center gap-6">
            <button className="w-20 h-20 bg-[#1e448a] hover:bg-[#15346b] text-white rounded-full flex items-center justify-center shadow-lg hover:scale-105 transition-all">
              <Mic size={32} />
            </button>
            <span className="text-slate-500 font-medium">
              ← Click para hablar
            </span>
          </div>
        </div>
      </div>
    </div>
  );
});
