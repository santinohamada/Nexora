"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState, type RefObject } from "react";
import { usePathname } from "next/navigation";
import { ShieldCheck } from "lucide-react";
import { useMediaPipeTasks } from "../../hooks/useMediaPipeTasks";
import { useChatChannel } from "../../hooks/useChatChannel";
import { useLiveTranslation } from "../../hooks/useLiveTranslation";
import { sendAudit } from "../../lib/audit";
import { Status } from "../../types";

const CONSENT_KEY = "nexora-camera-consent";

type Consent = "pending" | "accepted" | "declined";

type StationValue = ReturnType<typeof useChatChannel> & {
  consent: Consent;
  showConsentDialog: boolean;
  acceptConsent: () => void;
  declineConsent: () => void;
  reconsiderConsent: () => void;
  videoRef: (node: HTMLVideoElement | null) => void;
  canvasRef: RefObject<HTMLCanvasElement | null>;
  cameraStatus: Status;
  cameraError: string | null;
  showSkeleton: boolean;
  setShowSkeleton: (show: boolean) => void;
  showWords: boolean;
  setShowWords: (show: boolean) => void;
  stream: MediaStream | null;
  transcript: string;
  isProcessingSentence: boolean;
};

const StationContext = createContext<StationValue | null>(null);

export function StationProvider({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [consent, setConsent] = useState<Consent>("pending");
  const [showConsentDialog, setShowConsentDialog] = useState(false);
  const [showSkeleton, setShowSkeleton] = useState(true);
  const [showWords, setShowWords] = useState(true);
  const [cameraOn, setCameraOn] = useState(false);
  const chat = useChatChannel();
  const { onFrame, transcript, isProcessingSentence } = useLiveTranslation(chat.sendMessage);

  useEffect(() => {
    const saved = localStorage.getItem(CONSENT_KEY);
    if (saved === "accepted") {
      setConsent("accepted");
      return;
    }
    if (saved === "declined") {
      setConsent("declined");
      return;
    }
    setShowConsentDialog(true);
  }, []);

  const onStation = pathname === "/paciente" || pathname === "/recepcion";

  useEffect(() => {
    if (consent === "accepted" && onStation) setCameraOn(true);
  }, [consent, onStation]);

  const acceptConsent = useCallback(() => {
    localStorage.setItem(CONSENT_KEY, "accepted");
    setConsent("accepted");
    setShowConsentDialog(false);
  }, []);

  const declineConsent = useCallback(() => {
    localStorage.setItem(CONSENT_KEY, "declined");
    setConsent("declined");
  }, []);

  const reconsiderConsent = useCallback(() => {
    setConsent("pending");
    setShowConsentDialog(true);
  }, []);

  const media = useMediaPipeTasks({
    onFrame,
    drawLandmarksOnCanvas: showSkeleton,
    enabled: cameraOn,
  });

  const relayRef = useRef<HTMLVideoElement>(null);
  const consentDialogRef = useRef<HTMLDivElement>(null);
  const consentOpen = showConsentDialog && onStation;

  useEffect(() => {
    if (consentOpen) consentDialogRef.current?.focus();
  }, [consentOpen, consent]);

  useEffect(() => {
    const el = relayRef.current;
    if (!el || !media.stream) return;
    if (el.srcObject !== media.stream) el.srcObject = media.stream;
    el.play().catch(() => {});
  }, [media.stream]);

  useEffect(() => {
    if (!media.stream) return;
    const bc = new BroadcastChannel("nexora-camera");
    const shot = document.createElement("canvas");
    shot.width = 320;
    shot.height = 180;
    const ctx = shot.getContext("2d");
    const id = window.setInterval(() => {
      const video = relayRef.current;
      if (!ctx || !video || video.readyState < 2) return;
      ctx.drawImage(video, 0, 0, shot.width, shot.height);
      bc.postMessage(shot.toDataURL("image/jpeg", 0.5));
    }, 160);
    return () => {
      window.clearInterval(id);
      bc.close();
    };
  }, [media.stream]);

  const value: StationValue = {
    ...chat,
    consent,
    showConsentDialog: showConsentDialog && onStation,
    acceptConsent,
    declineConsent,
    reconsiderConsent,
    videoRef: media.videoRef,
    canvasRef: media.canvasRef,
    cameraStatus: media.status,
    cameraError: media.error,
    showSkeleton,
    setShowSkeleton,
    showWords,
    setShowWords,
    stream: media.stream,
    transcript,
    isProcessingSentence,
  };

  const station = pathname === "/recepcion" ? "recepcion" : "paciente";

  return (
    <StationContext.Provider value={value}>
      <video ref={relayRef} className="hidden" muted playsInline />
      {consentOpen && (
        <div className="fixed inset-0 z-[100] bg-slate-900/70 backdrop-blur-sm flex items-center justify-center p-6">
          <div
            ref={consentDialogRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby="consent-title"
            tabIndex={-1}
            className="bg-white rounded-[2rem] shadow-xl border border-slate-200 max-w-lg w-full p-8 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
          >
            <div className="flex items-center gap-3 mb-4">
              <ShieldCheck className="text-indigo-600" size={28} />
              <h2 id="consent-title" className="text-2xl font-bold text-slate-800">
                Consentimiento para usar la cámara
              </h2>
            </div>
            <p className="text-base text-slate-600 leading-relaxed mb-4">
              Usamos tu cámara solo para reconocer tus señas y traducirlas a
              texto y voz. No se guarda ningún video ni imagen: el
              procesamiento ocurre en este dispositivo.
            </p>
            {consent === "declined" && (
              <p className="text-base text-amber-800 bg-amber-50 border border-amber-200 rounded-xl p-4 mb-4">
                El traductor necesita la cámara para funcionar. Podés
                reconsiderar cuando quieras.
              </p>
            )}
            <div className="flex flex-col sm:flex-row gap-3 justify-end mt-4">
              {consent === "declined" ? (
                <button
                  type="button"
                  onClick={reconsiderConsent}
                  className="px-6 py-3 bg-indigo-600 text-white rounded-xl font-semibold hover:bg-indigo-700 transition-colors"
                >
                  Reconsiderar
                </button>
              ) : (
                <>
                  <button
                    type="button"
                    onClick={() => {
                      declineConsent();
                      sendAudit({ type: "consent", station, consent: "declined" });
                    }}
                    className="px-6 py-3 text-slate-600 hover:text-slate-800 hover:bg-slate-100 rounded-xl font-semibold transition-colors"
                  >
                    No acepto
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      acceptConsent();
                      sendAudit({ type: "consent", station, consent: "accepted" });
                    }}
                    className="px-6 py-3 bg-indigo-600 text-white rounded-xl font-semibold hover:bg-indigo-700 transition-colors"
                  >
                    Acepto y continúo
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      )}
      {children}
    </StationContext.Provider>
  );
}

export function useStation() {
  const value = useContext(StationContext);
  if (!value) throw new Error("useStation fuera de StationProvider");
  return value;
}
