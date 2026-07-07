import { memo } from "react";
import { ChatMessage } from "../../types";

export const ChatBubble = memo(function ChatBubble({
  msg,
}: {
  msg: ChatMessage;
}) {
  console.log("[Render] ChatBubble");
  const isPatient = msg.role === "PACIENTE";

  return (
    <div
      className={`flex flex-col max-w-[85%] ${isPatient ? "self-start" : "self-end items-end"}`}
    >
      <div
        className={`p-4 rounded-3xl relative shadow-sm ${
          isPatient
            ? "bg-white text-slate-800 rounded-tl-none border border-slate-200"
            : "bg-[#1e448a] text-white rounded-tr-none"
        }`}
      >
        <div
          className={`text-[10px] font-bold uppercase tracking-wider mb-1 ${isPatient ? "text-teal-500" : "text-blue-200"}`}
        >
          {msg.role}
        </div>
        <p className="text-[15px] leading-relaxed pb-4">{msg.text}</p>
        <span
          className={`absolute bottom-3 right-4 text-[10px] ${isPatient ? "text-slate-400" : "text-blue-300"}`}
        >
          {msg.time}
        </span>
      </div>
    </div>
  );
});
