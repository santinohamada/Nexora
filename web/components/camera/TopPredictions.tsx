import { memo } from "react";
import { PredictionResult } from "../../types";

export const TopPredictions = memo(function TopPredictions({
  prediction,
}: {
  prediction: PredictionResult | null;
}) {
  console.log("[Render] TopPredictions");
  if (!prediction || !prediction.top3) return null;

  return (
    <div className="w-full bg-slate-100 rounded-2xl p-4 shadow-sm border border-slate-200 mt-4">
      <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">
        Top-3 Predicciones
      </h4>
      <div className="flex flex-row justify-between gap-4">
        {prediction.top3.map((item, index) => (
          <div key={index} className="flex flex-col gap-1 flex-1">
            <div className="flex justify-between items-center text-xs">
              <span className="text-slate-700 font-bold capitalize">
                {item.sign}
              </span>
              <span className="text-indigo-600 font-bold">
                {item.confidence.toFixed(1)}%
              </span>
            </div>
            <div className="w-full bg-slate-200 rounded-full h-1.5 overflow-hidden">
              <div
                className={`h-full rounded-full ${
                  index === 0
                    ? "bg-indigo-500"
                    : index === 1
                      ? "bg-cyan-500"
                      : "bg-slate-500"
                }`}
                style={{ width: `${item.confidence}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
});
