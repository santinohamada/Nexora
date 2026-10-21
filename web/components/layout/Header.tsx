import { memo } from "react";
import { User, Activity } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";

export const Header = memo(function Header() {
  const pathname = usePathname();
  const isPaciente = pathname === "/paciente";
  const isRecepcion = pathname === "/recepcion";

  console.log("[Render] Header");
  return (
    <header className="flex justify-between items-center px-8 py-4 bg-white/50 backdrop-blur-md border-b border-slate-200/50 sticky top-0 z-50">
      <div className="flex items-center gap-3">
        <Link href="/">
          <Image
            src="/Imagotipo NEXORA_Final.png"
            alt="NEXORA Logo"
            width={100}
            height={100}
            className="h-16 w-auto object-contain cursor-pointer"
            priority
          />
        </Link>
      </div>

      <div className="flex bg-slate-100 p-1 rounded-full shadow-inner border border-slate-200/60">
        <Link
          href="/paciente"
          className={`flex items-center gap-2 px-5 py-2 rounded-full text-sm font-semibold transition-all ${
            isPaciente
              ? "bg-white text-indigo-600 shadow-sm ring-1 ring-slate-200/50"
              : "text-slate-600 hover:text-slate-800 hover:bg-slate-200/50"
          }`}
        >
          <User size={16} />
          Vista Paciente
        </Link>
        <Link
          href="/recepcion"
          className={`flex items-center gap-2 px-5 py-2 rounded-full text-sm font-semibold transition-all ${
            isRecepcion
              ? "bg-white text-indigo-600 shadow-sm ring-1 ring-slate-200/50"
              : "text-slate-600 hover:text-slate-800 hover:bg-slate-200/50"
          }`}
        >
          <Activity size={16} />
          Vista Recepción / Enfermería
        </Link>
      </div>
    </header>
  );
});
