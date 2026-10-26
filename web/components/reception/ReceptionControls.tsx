import { useState, useRef, memo, useCallback, useEffect } from "react";
import { Send, Mic, MicOff } from "lucide-react";
import { useSpeechToText } from "../../hooks/useSpeechToText";

export const ReceptionControls = memo(function ReceptionControls({
  onSend,
}: {
  onSend: (text: string) => void;
}) {
  console.log("[Render] ReceptionControls");
  const [receptionText, setReceptionText] = useState("");
  // Text already typed when dictation starts; the dictated segment is appended to it.
  const baseTextRef = useRef("");

  const handleSpeechResult = useCallback((text: string) => {
    const base = baseTextRef.current;
    setReceptionText(base ? base + " " + text : text);
  }, []);

  const { isListening, toggleListening, error, isSupported } = useSpeechToText(handleSpeechResult);
  const [micLevel, setMicLevel] = useState(0);

  useEffect(() => {
    if (!isListening) {
      setMicLevel(0);
      return;
    }
    let raf = 0;
    let stream: MediaStream | null = null;
    let audio: AudioContext | null = null;
    let cancelled = false;
    const smooth = { current: 0 };
    navigator.mediaDevices.getUserMedia({ audio: true }).then((media) => {
      if (cancelled) {
        media.getTracks().forEach((track) => track.stop());
        return;
      }
      stream = media;
      audio = new AudioContext();
      const source = audio.createMediaStreamSource(media);
      const analyser = audio.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      const samples = new Uint8Array(analyser.fftSize);
      const tick = () => {
        analyser.getByteTimeDomainData(samples);
        let sum = 0;
        for (let i = 0; i < samples.length; i++) {
          const v = (samples[i] - 128) / 128;
          sum += v * v;
        }
        const target = Math.min(1, Math.sqrt(sum / samples.length) * 5);
        smooth.current += (target - smooth.current) * 0.12;
        setMicLevel(smooth.current);
        raf = requestAnimationFrame(tick);
      };
      tick();
    }).catch(() => setMicLevel(0));
    return () => {
      cancelled = true;
      cancelAnimationFrame(raf);
      stream?.getTracks().forEach((track) => track.stop());
      audio?.close();
    };
  }, [isListening]);

  const handleToggleListening = () => {
    if (!isListening) baseTextRef.current = receptionText.trimEnd();
    toggleListening();
  };

  const handleSend = () => {
    if (!receptionText.trim()) return;
    onSend(receptionText.trim());
    setReceptionText("");
    baseTextRef.current = "";
  };

  return (
    <div>
      {!isSupported && (
        <p className="text-red-500 text-sm mb-2">
          El navegador no soporta reconocimiento de voz.
        </p>
      )}
      {error && (
        <p className="text-red-500 text-sm mb-2">
          Error de micrófono: {error}
        </p>
      )}
      <div className="flex items-center gap-2 bg-slate-100 border border-slate-200 rounded-full pl-4 pr-1.5 py-1.5">
        <input
          value={receptionText}
          onChange={(e) => setReceptionText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") handleSend();
          }}
          readOnly={isListening}
          placeholder="Escribir..."
          aria-label="Escribir respuesta"
          className="flex-1 min-w-0 bg-transparent text-slate-800 outline-none"
        />
        <div className="relative w-10 h-10 shrink-0">
          {isListening && (
            <span
              aria-hidden
              className="absolute left-1/2 top-1/2 w-10 h-10 rounded-full bg-red-400/45 blur-[2px] pointer-events-none"
              style={{ transform: `translate(-50%, -50%) scale(${1 + micLevel * 0.9})` }}
            />
          )}
          <button
            type="button"
            onClick={handleToggleListening}
            aria-label={isListening ? "Detener dictado" : "Dictar respuesta por voz"}
            disabled={!isSupported}
            className={`relative z-10 w-10 h-10 rounded-full flex items-center justify-center ${
              isListening
                ? "bg-red-600 text-white"
                : "bg-[#1e448a] text-white disabled:opacity-50"
            }`}
          >
            {isListening ? <MicOff size={18} /> : <Mic size={18} />}
          </button>
        </div>
        <button
          type="button"
          onClick={handleSend}
          disabled={!receptionText.trim()}
          className="shrink-0 w-10 h-10 rounded-full bg-[#1e448a] hover:bg-[#15346b] disabled:opacity-40 text-white flex items-center justify-center"
          aria-label="Enviar"
        >
          <Send size={18} />
        </button>
      </div>
      {isListening && (
        <p className="mt-2 text-sm text-red-500">Escuchando... click para detener</p>
      )}
    </div>
  );
});
