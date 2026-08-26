import { useState, useRef, useEffect, useCallback } from "react";
import { ChatMessage, Frame } from "../types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const DEFAULT_DISPLAY_WINDOW_MS = 3000;
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

const DEFAULT_IDLE_MS = 800;
const IDLE_MS = (() => {
  const raw = process.env.NEXT_PUBLIC_LATENCY_V2_IDLE_MS;
  if (raw === undefined || raw === null || raw === "") {
    return DEFAULT_IDLE_MS;
  }
  const parsed = Number.parseInt(raw, 10);
  if (!Number.isFinite(parsed) || parsed < 0) {
    return DEFAULT_IDLE_MS;
  }
  return parsed;
})();

const DEFAULT_QUIET_THRESHOLD = 0.005;
const QUIETNESS_THRESHOLD = (() => {
  const raw = process.env.NEXT_PUBLIC_LATENCY_V2_QUIETNESS_THRESHOLD;
  if (raw === undefined || raw === null || raw === "") {
    return DEFAULT_QUIET_THRESHOLD;
  }
  const parsed = Number.parseFloat(raw);
  if (!Number.isFinite(parsed) || parsed < 0) {
    return DEFAULT_QUIET_THRESHOLD;
  }
  return parsed;
})();

const DEFAULT_QUIET_WINDOW = 6;
const QUIETNESS_WINDOW = (() => {
  const raw = process.env.NEXT_PUBLIC_LATENCY_V2_QUIETNESS_FRAMES;
  if (raw === undefined || raw === null || raw === "") {
    return DEFAULT_QUIET_WINDOW;
  }
  const parsed = Number.parseInt(raw, 10);
  if (!Number.isFinite(parsed) || parsed < 1) {
    return DEFAULT_QUIET_WINDOW;
  }
  return parsed;
})();

function computeFrameMagnitude(prev: Frame, cur: Frame): number {
  let total = 0;
  const len = Math.min(prev.length, cur.length);
  for (let i = 0; i < len; i++) {
    const dx = cur[i][0] - prev[i][0];
    const dy = cur[i][1] - prev[i][1];
    const dz = cur[i][2] - prev[i][2];
    total += Math.sqrt(dx * dx + dy * dy + dz * dz);
  }
  return len > 0 ? total / len : 0;
}

export function useSentenceBuilder(
  onNewPatientMessage: (msg: ChatMessage) => void
) {
  const [transcript, setTranscript] = useState<string>("");
  const [isProcessingSentence, setIsProcessingSentence] = useState(false);
  const transcriptRef = useRef<string>("");
  const lastWordRef = useRef<string>("");
  const isProcessingRef = useRef<boolean>(false);
  const displayTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const quietFramesRef = useRef<number[]>([]);
  const lastFrameRef = useRef<Frame | null>(null);
  const lastNonIdlePredictionTsRef = useRef<number>(performance.now());

  useEffect(() => {
    isProcessingRef.current = isProcessingSentence;
  }, [isProcessingSentence]);

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
    if (sentence.trim().length === 0) return;

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
      setIsProcessingSentence(false);
    }
  }, [onNewPatientMessage, cancelDisplayTimer]);

  const tryCloseSentence = useCallback(() => {
    if (transcriptRef.current.trim().length === 0) return;
    if (isProcessingRef.current) return;
    if (quietFramesRef.current.length < QUIETNESS_WINDOW) return;

    let sum = 0;
    for (const x of quietFramesRef.current) sum += x;
    const mean = sum / quietFramesRef.current.length;

    const idleElapsed =
      performance.now() - lastNonIdlePredictionTsRef.current;

    if (mean < QUIETNESS_THRESHOLD && idleElapsed >= IDLE_MS) {
      processSentence();
    }
  }, [processSentence]);

  const onFrameTick = useCallback(
    (frame: Frame) => {
      if (lastFrameRef.current) {
        const magnitude = computeFrameMagnitude(lastFrameRef.current, frame);
        quietFramesRef.current.push(magnitude);
        if (quietFramesRef.current.length > QUIETNESS_WINDOW) {
          quietFramesRef.current.shift();
        }
      }
      lastFrameRef.current = frame;
      tryCloseSentence();
    },
    [tryCloseSentence]
  );

  const addWord = useCallback(
    (word: string) => {
      lastNonIdlePredictionTsRef.current = performance.now();
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
    onFrameTick,
  };
}
