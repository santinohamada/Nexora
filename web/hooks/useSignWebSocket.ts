import { useEffect, useRef, useState, useCallback } from "react";
import { PredictionResult, Frame, Landmark } from "../types";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";
const LATENCY_TIMING_ENABLED =
  process.env.NEXT_PUBLIC_LATENCY_V2_TIMING === "on";
const WS_PROTOCOL_VERSION = (
  process.env.NEXT_PUBLIC_WS_PROTOCOL || "v1"
).toLowerCase();
const USE_BINARY_V2 = WS_PROTOCOL_VERSION === "v2";

const POSE_LANDMARKS = 33;
const HAND_LANDMARKS = 21;
const POSE_FLOATS = POSE_LANDMARKS * 3;
const HAND_FLOATS = HAND_LANDMARKS * 3;
const HEADER_BYTES = 4;
const FLAG_LEFT_OMIT = 0x01;
const FLAG_RIGHT_OMIT = 0x02;
const COORDINATE_DECIMALS = 10000;

function isHandEmpty(hand: Landmark[]): boolean {
  return hand.every((lm) => lm[3] === 0);
}

function roundCoord(value: number): number {
  return Math.round(value * COORDINATE_DECIMALS) / COORDINATE_DECIMALS;
}

function packFramesBinary(frames: Frame[]): ArrayBuffer {
  const T = frames.length;
  const anyLeftEmpty = frames.some((f) =>
    isHandEmpty(f.slice(POSE_LANDMARKS, POSE_LANDMARKS + HAND_LANDMARKS))
  );
  const anyRightEmpty = frames.some((f) =>
    isHandEmpty(f.slice(POSE_LANDMARKS + HAND_LANDMARKS, POSE_LANDMARKS + 2 * HAND_LANDMARKS))
  );

  const floatsPerFrame =
    POSE_FLOATS +
    (anyLeftEmpty ? 0 : HAND_FLOATS) +
    (anyRightEmpty ? 0 : HAND_FLOATS);

  const totalFloats = T * floatsPerFrame;
  const buf = new ArrayBuffer(HEADER_BYTES + totalFloats * 4);
  const view = new DataView(buf);
  view.setUint8(0, 0x02);
  let flags = 0;
  if (anyLeftEmpty) flags |= FLAG_LEFT_OMIT;
  if (anyRightEmpty) flags |= FLAG_RIGHT_OMIT;
  view.setUint8(1, flags);
  view.setUint8(2, 0);
  view.setUint8(3, 0);

  const arr = new Float32Array(buf, HEADER_BYTES);
  let offset = 0;
  for (let i = 0; i < T; i++) {
    const f = frames[i];
    for (let j = 0; j < POSE_LANDMARKS; j++) {
      arr[offset++] = roundCoord(f[j][0]);
      arr[offset++] = roundCoord(f[j][1]);
      arr[offset++] = roundCoord(f[j][2]);
    }
    if (!anyLeftEmpty) {
      const leftStart = POSE_LANDMARKS;
      for (let j = 0; j < HAND_LANDMARKS; j++) {
        const lm = f[leftStart + j];
        arr[offset++] = roundCoord(lm[0]);
        arr[offset++] = roundCoord(lm[1]);
        arr[offset++] = roundCoord(lm[2]);
      }
    }
    if (!anyRightEmpty) {
      const rightStart = POSE_LANDMARKS + HAND_LANDMARKS;
      for (let j = 0; j < HAND_LANDMARKS; j++) {
        const lm = f[rightStart + j];
        arr[offset++] = roundCoord(lm[0]);
        arr[offset++] = roundCoord(lm[1]);
        arr[offset++] = roundCoord(lm[2]);
      }
    }
  }
  return buf;
}

export function useSignWebSocket({ onMessage }: { onMessage?: (data: PredictionResult) => void } = {}) {
  const [wsStatus, setWsStatus] = useState<
    "connecting" | "connected" | "disconnected"
  >("connecting");
  const wsRef = useRef<WebSocket | null>(null);
  const isPredictingRef = useRef(false);
  const sendTimestampRef = useRef<number | null>(null);
  const onMessageRef = useRef(onMessage);

  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);

  useEffect(() => {
    let ws: WebSocket | null = null;
    let reconnectTimeout: NodeJS.Timeout;

    const connect = () => {
      const url = USE_BINARY_V2
        ? `${WS_URL}/ws/predict?v=2`
        : `${WS_URL}/ws/predict?v=1`;
      ws = new WebSocket(url);
      if (USE_BINARY_V2) {
        ws.binaryType = "arraybuffer";
      }
      wsRef.current = ws;

      ws.onopen = () => setWsStatus("connected");

      ws.onmessage = (event) => {
        try {
          let data: PredictionResult | null = null;
          if (USE_BINARY_V2 && event.data instanceof ArrayBuffer) {
            const view = new Uint8Array(event.data);
            if (view.byteLength === 0) {
              return;
            }
            const decoder = new TextDecoder();
            const text = decoder.decode(view);
            data = JSON.parse(text);
          } else if (typeof event.data === "string") {
            data = JSON.parse(event.data);
          } else if (event.data instanceof Blob) {
            return;
          } else {
            return;
          }
          isPredictingRef.current = false;
          if (LATENCY_TIMING_ENABLED && sendTimestampRef.current !== null) {
            const wsRoundtripMs = performance.now() - sendTimestampRef.current;
            sendTimestampRef.current = null;
            console.debug(
              `[Nexora timing] stage=ws_roundtrip_ms ms=${wsRoundtripMs.toFixed(2)}`,
            );
          }
          if (data && data.sign && data.confidence !== undefined) {
            onMessageRef.current?.(data);
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
    if (LATENCY_TIMING_ENABLED) {
      sendTimestampRef.current = performance.now();
    }
    if (USE_BINARY_V2) {
      const payload = packFramesBinary(frames);
      wsRef.current.send(payload);
    } else {
      wsRef.current.send(JSON.stringify({ frames }));
    }
  }, []);

  return { wsStatus, sendFrames };
}
