import { useCallback, useRef } from "react";
import { useSentenceBuilder } from "./useSentenceBuilder";
import { useSignWebSocket } from "./useSignWebSocket";
import { ChatMessage, Frame, PredictionResult } from "../types";

const CONFIDENCE_THRESHOLD = 70;

function readIntEnv(name: string, fallback: number): number {
  const raw = process.env[name];
  if (raw === undefined || raw === null || raw === "") return fallback;
  const parsed = Number.parseInt(raw, 10);
  if (!Number.isFinite(parsed) || parsed < 1) return fallback;
  return parsed;
}

const RECORDING_MAX_FRAMES = readIntEnv("NEXT_PUBLIC_RECORDING_MAX_FRAMES", 45);
const PREDICT_STRIDE_FRAMES = readIntEnv("NEXT_PUBLIC_SEND_STRIDE", 8);

export function useLiveTranslation(sendMessage: (msg: ChatMessage) => void) {
  const recordedFrames = useRef<Frame[]>([]);
  const framesSinceLastPredictRef = useRef(0);

  const { transcript, isProcessingSentence, addWord, processSentence } =
    useSentenceBuilder(sendMessage);

  const handleNewPrediction = useCallback(
    (data: PredictionResult) => {
      if (data.top3) {
        data.top3.forEach((item, index) => {
          const signEl = document.getElementById(`pred-sign-${index}`);
          if (signEl) signEl.innerText = item.sign;
          const confEl = document.getElementById(`pred-conf-${index}`);
          if (confEl) confEl.innerText = `${item.confidence.toFixed(1)}%`;
          const barEl = document.getElementById(`pred-bar-${index}`);
          if (barEl) barEl.style.width = `${item.confidence}%`;
        });
      }

      if (data.sign === "idle") {
        if (data.confidence >= CONFIDENCE_THRESHOLD) processSentence();
      } else {
        const idleDominant = (data.top3 ?? []).some(
          (item) => item.sign === "idle" && item.confidence > 50
        );
        if (!idleDominant && data.confidence >= CONFIDENCE_THRESHOLD) {
          addWord(data.sign);
        }
      }
    },
    [addWord, processSentence]
  );

  const { sendFrames } = useSignWebSocket({ onMessage: handleNewPrediction });

  const onFrame = useCallback(
    (frameData: Frame) => {
      recordedFrames.current.push(frameData);
      if (recordedFrames.current.length > RECORDING_MAX_FRAMES) {
        recordedFrames.current.shift();
      }
      framesSinceLastPredictRef.current++;
      if (
        recordedFrames.current.length >= 20 &&
        framesSinceLastPredictRef.current >= PREDICT_STRIDE_FRAMES
      ) {
        sendFrames([...recordedFrames.current]);
        framesSinceLastPredictRef.current = 0;
      }
    },
    [sendFrames]
  );

  return { onFrame, transcript, isProcessingSentence };
}
