"use client";

import { useEffect, useRef, useState } from "react";
import { Pencil } from "lucide-react";
import { useStation } from "../stations/StationProvider";

export function ReceptionChatHeader() {
  const { attendantName, setAttendantName } = useStation();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(attendantName);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setDraft(attendantName);
  }, [attendantName]);

  useEffect(() => {
    if (editing) inputRef.current?.focus();
  }, [editing]);

  const commit = () => {
    setAttendantName(draft);
    setEditing(false);
  };

  const displayName = attendantName || "sin definir";

  return (
    <div className="flex flex-col gap-1 min-w-0 flex-1">
      <h3 className="text-lg font-bold text-slate-800">Conversación con paciente</h3>
      <div className="flex items-center gap-2 min-w-0">
        {editing ? (
          <>
            <span className="text-sm text-slate-600 shrink-0">Tu nombre:</span>
            <input
              ref={inputRef}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onBlur={commit}
              onKeyDown={(e) => {
                if (e.key === "Enter") commit();
                if (e.key === "Escape") {
                  setDraft(attendantName);
                  setEditing(false);
                }
              }}
              aria-label="Tu nombre"
              placeholder="Tu nombre acá"
              className="min-w-0 flex-1 max-w-[14rem] text-sm text-slate-800 border border-slate-300 rounded-lg px-2 py-1 outline-none focus:border-[#1e448a] focus:ring-1 focus:ring-[#1e448a]"
            />
          </>
        ) : (
          <span className="text-sm text-slate-600 truncate">
            Tu nombre:{" "}
            <span className={attendantName ? "text-slate-800 font-medium" : "text-slate-400 italic"}>
              {displayName}
            </span>
          </span>
        )}
        <button
          type="button"
          onClick={() => setEditing(true)}
          aria-label="Editar tu nombre"
          className="shrink-0 p-1.5 text-slate-500 hover:text-[#1e448a] hover:bg-slate-100 rounded-lg transition-colors"
        >
          <Pencil size={16} />
        </button>
      </div>
    </div>
  );
}
