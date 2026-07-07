import { memo } from "react";
import { Activity, ShieldCheck } from "lucide-react";
import { PredictionResult } from "../../types";

export const Footer = memo(function Footer({
  prediction,
  wsStatus,
}: {
  prediction: PredictionResult | null;
  wsStatus: string;
}) {
  console.log("[Render] Footer");
  return (
    <footer className="fixed bottom-0 left-0 w-full bg-slate-100/80 backdrop-blur-md border-t border-slate-200 px-6 py-2 flex justify-between items-center text-xs font-mono text-slate-500 z-50">
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2">
          <span
            className={`w-2 h-2 rounded-full ${wsStatus === "connected" ? "bg-emerald-500" : "bg-red-500"}`}
          />
          WebSocket:{" "}
          <span className="font-bold text-slate-700">
            {wsStatus === "connected" ? "Conectado" : "Desconectado"}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <Activity size={14} className="text-emerald-500" />
          Confianza IA:{" "}
          <span className="font-bold text-slate-700">
            {prediction ? `${prediction.confidence.toFixed(0)}%` : "—"}
          </span>
        </div>
      </div>
      <div className="flex items-center gap-2 bg-emerald-100 text-emerald-800 px-3 py-1 rounded-full font-sans font-medium text-xs">
        <ShieldCheck size={14} />
        Estado: Procesamiento Local Seguro (0% Almacenamiento Persistente)
      </div>
    </footer>
  );
});
