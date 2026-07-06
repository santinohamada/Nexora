import { memo } from "react";
import { User, Activity } from "lucide-react";
import Image from "next/image";

export const Header = memo(function Header({
  view,
  setView,
}: {
  view: "paciente" | "recepcion";
  setView: (v: "paciente" | "recepcion") => void;
}) {
  console.log("[Render] Header");
  return (
    <header className="flex justify-between items-center px-8 py-4 bg-white/50 backdrop-blur-md border-b border-slate-200/50 sticky top-0 z-50">
      <div className="flex items-center gap-3">
        <Image
          src="/Imagotipo NEXORA_Final.png"
          alt="NEXORA Logo"
          width={100}
          height={100}
          className="h-16 w-auto object-contain"
          priority
        />
      </div>

      <div className="flex bg-slate-100 p-1 rounded-full shadow-inner border border-slate-200/60">
        <button
          onClick={() => setView("paciente")}
          className={`flex items-center gap-2 px-5 py-2 rounded-full text-sm font-semibold transition-all ${
            view === "paciente"
              ? "bg-white text-indigo-600 shadow-sm ring-1 ring-slate-200/50"
              : "text-slate-500 hover:text-slate-700 hover:bg-slate-200/50"
          }`}
        >
          <User size={16} />
          Vista Paciente
        </button>
        <button
          onClick={() => setView("recepcion")}
          className={`flex items-center gap-2 px-5 py-2 rounded-full text-sm font-semibold transition-all ${
            view === "recepcion"
              ? "bg-white text-indigo-600 shadow-sm ring-1 ring-slate-200/50"
              : "text-slate-500 hover:text-slate-700 hover:bg-slate-200/50"
          }`}
        >
          <Activity size={16} />
          Vista Recepción / Enfermería
        </button>
      </div>
    </header>
  );
});
