import { useState, memo, useCallback, useEffect } from "react";
import { Send, Mic, MicOff } from "lucide-react";
import { useSpeechToText } from "../../hooks/useSpeechToText";

export const ReceptionControls = memo(function ReceptionControls({
  onSend,
}: {
  onSend: (text: string) => void;
}) {
  console.log("[Render] ReceptionControls");
  const [receptionText, setReceptionText] = useState("");
  const [baseText, setBaseText] = useState("");

  const handleSpeechResult = useCallback((text: string) => {
    // Si ya había texto escrito, le agregamos el texto dictado
    if (baseText) {
      setReceptionText(baseText + " " + text);
    } else {
      setReceptionText(text);
    }
  }, [baseText]);

  const { isListening, toggleListening, error, isSupported } = useSpeechToText(handleSpeechResult);

  // Cuando termina de escuchar (isListening pasa a false), guardamos el texto actual como base
  // para que si vuelve a iniciar dictado no lo pise.
  useEffect(() => {
    if (isListening) {
      setBaseText(receptionText);
    }
  }, [isListening]);


  const handleSend = () => {
    if (!receptionText.trim()) return;
    onSend(receptionText.trim());
    setReceptionText("");
    setBaseText("");
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
        <div className="flex-1 flex flex-col items-center justify-center">
          {!isSupported && (
            <p className="text-red-500 text-sm mb-4">
              El navegador no soporta reconocimiento de voz.
            </p>
          )}
          {error && (
            <p className="text-red-500 text-sm mb-4">
              Error de micrófono: {error}
            </p>
          )}
          <div className="flex items-center gap-6">
            <button
              onClick={toggleListening}
              disabled={!isSupported}
              className={`w-20 h-20 rounded-full flex items-center justify-center shadow-lg hover:scale-105 transition-all ${
                isListening
                  ? "bg-red-600 hover:bg-red-700 animate-pulse text-white ring-4 ring-red-200"
                  : "bg-[#1e448a] hover:bg-[#15346b] text-white disabled:opacity-50"
              }`}
            >
              {isListening ? <MicOff size={32} /> : <Mic size={32} />}
            </button>
            <span className={`font-medium ${isListening ? "text-red-500" : "text-slate-500"}`}>
              {isListening ? "Escuchando... click para detener" : "← Click para hablar"}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
});
