import Link from "next/link";
import Image from "next/image";
import { User, Activity } from "lucide-react";

export default function LandingPage() {
  return (
    <main className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-8">
      <div className="bg-white p-12 rounded-[3rem] shadow-xl border border-slate-200/50 max-w-4xl w-full flex flex-col items-center text-center">
        <Image
          src="/Imagotipo NEXORA_Final.png"
          alt="NEXORA Logo"
          width={200}
          height={200}
          className="h-24 w-auto object-contain mb-8"
          priority
        />
        
        <h1 className="text-4xl font-bold text-slate-800 mb-4">
          Bienvenido a Nexora
        </h1>
        <p className="text-lg text-slate-500 mb-12 max-w-2xl">
          Selecciona la estación que deseas abrir. Para un entorno de doble monitor, abre cada enlace en una ventana y pantalla diferente.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 w-full max-w-2xl">
          <Link
            href="/paciente"
            className="flex flex-col items-center p-8 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 rounded-3xl transition-all hover:scale-105"
          >
            <div className="bg-indigo-600 text-white p-4 rounded-full mb-4 shadow-md">
              <User size={32} />
            </div>
            <h2 className="text-xl font-bold text-indigo-900 mb-2">Estación del Paciente</h2>
            <p className="text-indigo-700/80 text-sm">Cámara, captura de señas y traductor IA en tiempo real.</p>
          </Link>

          <Link
            href="/recepcion"
            className="flex flex-col items-center p-8 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 rounded-3xl transition-all hover:scale-105"
          >
            <div className="bg-emerald-600 text-white p-4 rounded-full mb-4 shadow-md">
              <Activity size={32} />
            </div>
            <h2 className="text-xl font-bold text-emerald-900 mb-2">Estación de Recepción</h2>
            <p className="text-emerald-700/80 text-sm">Panel de control, chat y respuestas de enfermería.</p>
          </Link>
        </div>
      </div>
    </main>
  );
}
