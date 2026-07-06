import { useEffect, useRef, useState, useCallback } from "react";
import { PredictionResult, Frame } from "../types";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";

export function useSignWebSocket() {
  const [prediction, setPrediction] = useState<PredictionResult | null>(null);
  const [wsStatus, setWsStatus] = useState<
    "connecting" | "connected" | "disconnected"
  >("connecting");
  const wsRef = useRef<WebSocket | null>(null);
  const isPredictingRef = useRef(false);

  useEffect(() => {
    let ws: WebSocket | null = null;
    let reconnectTimeout: NodeJS.Timeout;

    const connect = () => {
      ws = new WebSocket(`${WS_URL}/ws/predict`);
      wsRef.current = ws;

      ws.onopen = () => setWsStatus("connected");

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          isPredictingRef.current = false;
          if (data.sign && data.confidence !== undefined) {
            setPrediction(data);
          }
        } catch {
          isPredictingRef.current = false;
        }
      };

      ws.onclose = () => {
        wsRef.current = null;
        setWsStatus("disconnected");
        reconnectTimeout = setTimeout(connect, 2000);
      };

      ws.onerror = () => {
        isPredictingRef.current = false;
      };
    };

    connect();

    return () => {
      clearTimeout(reconnectTimeout);
      if (ws) ws.close();
    };
  }, []);

  const sendFrames = useCallback((frames: Frame[]) => {
    if (
      isPredictingRef.current ||
      !wsRef.current ||
      wsRef.current.readyState !== WebSocket.OPEN
    )
      return;
    isPredictingRef.current = true;
    wsRef.current.send(JSON.stringify({ frames }));
  }, []);

  return { prediction, wsStatus, sendFrames };
}
