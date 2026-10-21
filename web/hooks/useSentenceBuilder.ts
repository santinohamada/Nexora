import { useState, useRef, useEffect, useCallback } from "react";
import { ChatMessage } from "../types";
import { sendAudit } from "../lib/audit";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const DEFAULT_DISPLAY_WINDOW_MS = 1000;
const DISPLAY_WINDOW_MS = (() => {
  const raw = process.env.NEXT_PUBLIC_LATENCY_V2_DISPLAY_WINDOW_MS;
  if (raw === undefined || raw === null || raw === "") {
    return DEFAULT_DISPLAY_WINDOW_MS;
  }
  const parsed = Number.parseInt(raw, 10);
  if (!Number.isFinite(parsed) || parsed < 0) {
    return DEFAULT_DISPLAY_WINDOW_MS;
  }
  return parsed;
})();

export function useSentenceBuilder(
  onNewPatientMessage: (msg: ChatMessage) => void
) {
  const [transcript, setTranscript] = useState<string>("");
  const [isProcessingSentence, setIsProcessingSentence] = useState(false);
  const transcriptRef = useRef<string>("");
  const lastWordRef = useRef<string>("");
  const displayTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  // One sentence in flight at a time: idle predictions keep arriving while hands are down, and a
  // second concurrent request could reorder bubbles and cancel the first one's audio.
  const inFlightRef = useRef(false);

  const cancelDisplayTimer = useCallback(() => {
    if (displayTimerRef.current !== null) {
      clearTimeout(displayTimerRef.current as ReturnType<typeof setTimeout>);
      displayTimerRef.current = null;
    }
  }, []);

  useEffect(() => {
    return () => {
      cancelDisplayTimer();
    };
  }, [cancelDisplayTimer]);

  const processSentence = useCallback(async () => {
    const sentence = transcriptRef.current;
    if (sentence.trim().length === 0 || inFlightRef.current) return;
    inFlightRef.current = true;

    const closeTs = performance.now();
    setTranscript("");
    transcriptRef.current = "";
    lastWordRef.current = "";
    setIsProcessingSentence(true);

    try {
      const res = await fetch(`${API_URL}/process_sentence`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ words: sentence }),
      });
      if (res.ok) {
        const data = await res.json();

        if (data.natural_sentence && data.natural_sentence !== "NO_CLARO") {
          onNewPatientMessage({
            id: Date.now(),
            role: "PACIENTE",
            text: data.natural_sentence,
            words: sentence.split(" ").filter(Boolean),
            time: new Date().toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            }),
          });
          sendAudit({
            type: "translation_displayed",
            station: "paciente",
            e2e_ms: performance.now() - closeTs,
          });
        }

        if (data.audio_base64) {
          const audioUrl = "data:audio/wav;base64," + data.audio_base64;
          if (DISPLAY_WINDOW_MS <= 0) {
            new Audio(audioUrl).play();
          } else {
            cancelDisplayTimer();
            displayTimerRef.current = setTimeout(() => {
              displayTimerRef.current = null;
              new Audio(audioUrl).play();
            }, DISPLAY_WINDOW_MS);
          }
        }
      }
    } catch (e) {
      console.error("Error processing sentence", e);
    } finally {
      inFlightRef.current = false;
      setIsProcessingSentence(false);
    }
  }, [onNewPatientMessage, cancelDisplayTimer]);

  const addWord = useCallback(
    (word: string) => {
      if (word) {
        cancelDisplayTimer();
      }
      if (word && word !== lastWordRef.current) {
        lastWordRef.current = word;
        transcriptRef.current += transcriptRef.current ? " " + word : word;
        setTranscript(transcriptRef.current);
      }
    },
    [cancelDisplayTimer]
  );

  return {
    transcript,
    isProcessingSentence,
    addWord,
    processSentence,
  };
}
