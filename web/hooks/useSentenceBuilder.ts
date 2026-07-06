import { useState, useRef, useEffect, useCallback } from "react";
import { ChatMessage } from "../types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function useSentenceBuilder(
  onNewPatientMessage: (msg: ChatMessage) => void
) {
  const [transcript, setTranscript] = useState<string>("");
  const [isProcessingSentence, setIsProcessingSentence] = useState(false);
  const transcriptRef = useRef<string>("");
  const lastWordRef = useRef<string>("");

  const addWord = useCallback((word: string) => {
    if (word && word !== lastWordRef.current) {
      lastWordRef.current = word;
      transcriptRef.current += transcriptRef.current ? " " + word : word;
      setTranscript(transcriptRef.current);
    }
  }, []);

  const processSentence = useCallback(async () => {
    const sentence = transcriptRef.current;
    if (sentence.trim().length === 0) return;

    // Clear state immediately to prevent double submissions
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
            time: new Date().toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            }),
          });
        }

        if (data.audio_base64) {
          const audio = new Audio("data:audio/wav;base64," + data.audio_base64);
          audio.play();
        }
      }
    } catch (e) {
      console.error("Error processing sentence", e);
    } finally {
      setIsProcessingSentence(false);
    }
  }, [onNewPatientMessage]);

  return { transcript, isProcessingSentence, addWord, processSentence };
}
