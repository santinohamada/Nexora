import { useState, useEffect, useCallback } from "react";
import { ChatMessage } from "../types";

type ChatEvent =
  | { type: "MESSAGE"; payload: ChatMessage }
  | { type: "CLEAR" };

export function useChatChannel() {
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [channel, setChannel] = useState<BroadcastChannel | null>(null);

  useEffect(() => {
    const bc = new BroadcastChannel("nexora-chat");
    setChannel(bc);

    bc.onmessage = (event: MessageEvent<ChatEvent>) => {
      const data = event.data;
      if (data.type === "MESSAGE") {
        setChatHistory((prev) => {
          // Prevent duplicates if multiple tabs trigger somehow
          if (prev.some((m) => m.id === data.payload.id)) return prev;
          return [...prev, data.payload];
        });
      } else if (data.type === "CLEAR") {
        setChatHistory([]);
      }
    };

    return () => {
      bc.close();
    };
  }, []);

  const sendMessage = useCallback(
    (msg: ChatMessage) => {
      setChatHistory((prev) => [...prev, msg]);
      if (channel) {
        channel.postMessage({ type: "MESSAGE", payload: msg });
      }
    },
    [channel]
  );

  const clearHistory = useCallback(() => {
    setChatHistory([]);
    if (channel) {
      channel.postMessage({ type: "CLEAR" });
    }
  }, [channel]);

  return { chatHistory, sendMessage, clearHistory };
}
