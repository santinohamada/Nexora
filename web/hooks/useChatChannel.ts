import { useState, useEffect, useCallback } from "react";
import { ChatMessage } from "../types";

type ChatEvent =
  | { type: "MESSAGE"; payload: ChatMessage }
  | { type: "REPORTED"; id: number }
  | { type: "CLEAR" }
  | { type: "ATTENDANT_NAME"; name: string }
  | { type: "DELETE"; id: number };

const ATTENDANT_NAME_KEY = "nexora-attendant-name";

const flagReported = (history: ChatMessage[], id: number) =>
  history.map((m) => (m.id === id && !m.reported ? { ...m, reported: true } : m));

export function useChatChannel() {
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [attendantName, setAttendantNameState] = useState("");
  const [channel, setChannel] = useState<BroadcastChannel | null>(null);

  useEffect(() => {
    const saved = localStorage.getItem(ATTENDANT_NAME_KEY);
    if (saved) setAttendantNameState(saved);
  }, []);

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
      } else if (data.type === "REPORTED") {
        setChatHistory((prev) => flagReported(prev, data.id));
      } else if (data.type === "CLEAR") {
        setChatHistory([]);
      } else if (data.type === "ATTENDANT_NAME") {
        setAttendantNameState(data.name);
        if (data.name) localStorage.setItem(ATTENDANT_NAME_KEY, data.name);
        else localStorage.removeItem(ATTENDANT_NAME_KEY);
      } else if (data.type === "DELETE") {
        setChatHistory((prev) => prev.filter((m) => m.id !== data.id));
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

  // Marks a message as reported in this tab and notifies the other station face (CU-10).
  const markReported = useCallback(
    (id: number) => {
      setChatHistory((prev) => flagReported(prev, id));
      if (channel) {
        channel.postMessage({ type: "REPORTED", id });
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

  const setAttendantName = useCallback(
    (name: string) => {
      const trimmed = name.trim();
      setAttendantNameState(trimmed);
      if (trimmed) localStorage.setItem(ATTENDANT_NAME_KEY, trimmed);
      else localStorage.removeItem(ATTENDANT_NAME_KEY);
      channel?.postMessage({ type: "ATTENDANT_NAME", name: trimmed });
    },
    [channel]
  );

  const deleteMessage = useCallback(
    (id: number) => {
      setChatHistory((prev) => prev.filter((m) => m.id !== id));
      channel?.postMessage({ type: "DELETE", id });
    },
    [channel]
  );

  return {
    chatHistory,
    sendMessage,
    markReported,
    clearHistory,
    deleteMessage,
    attendantName,
    setAttendantName,
  };
}
