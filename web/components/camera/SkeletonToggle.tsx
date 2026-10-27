export function SkeletonToggle({
  checked,
  onChange,
  label = "Mostrar esqueleto",
}: {
  checked: boolean;
  onChange: (show: boolean) => void;
  label?: string;
}) {
  return (
    <label className="mt-4 flex items-center gap-3 text-sm font-medium text-slate-700 cursor-pointer">
      <input
        type="checkbox"
        role="switch"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="h-5 w-9 appearance-none rounded-full bg-slate-300 checked:bg-indigo-600 relative cursor-pointer transition-colors before:absolute before:top-0.5 before:left-0.5 before:h-4 before:w-4 before:rounded-full before:bg-white before:transition-transform checked:before:translate-x-4"
        aria-label={label}
      />
      {label}
    </label>
  );
}

export function SignCaption({
  show,
  transcript,
  busy,
}: {
  show: boolean;
  transcript: string;
  busy: boolean;
}) {
  if (!show || (!transcript && !busy)) return null;
  return (
    <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-30 bg-slate-900/95 border border-slate-700 px-6 py-3 rounded-full shadow-lg flex items-center gap-3 max-w-[80%]">
      {busy ? (
        <div className="flex items-center gap-3">
          <div className="w-4 h-4 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin" />
          <span className="text-sm font-medium text-indigo-300">
            Generando respuesta de IA...
          </span>
        </div>
      ) : (
        <span className="text-sm font-medium text-white truncate">{transcript}</span>
      )}
    </div>
  );
}
