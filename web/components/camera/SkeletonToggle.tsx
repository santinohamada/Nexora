export function SkeletonToggle({
  checked,
  onChange,
}: {
  checked: boolean;
  onChange: (show: boolean) => void;
}) {
  return (
    <label className="mt-4 flex items-center gap-3 text-sm font-medium text-slate-700 cursor-pointer">
      <input
        type="checkbox"
        role="switch"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="h-5 w-9 appearance-none rounded-full bg-slate-300 checked:bg-indigo-600 relative cursor-pointer transition-colors before:absolute before:top-0.5 before:left-0.5 before:h-4 before:w-4 before:rounded-full before:bg-white before:transition-transform checked:before:translate-x-4"
        aria-label="Mostrar esqueleto"
      />
      Mostrar esqueleto
    </label>
  );
}
