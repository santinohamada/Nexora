import { memo } from "react";
import { PredictionResult } from "../../types";

export function TopPredictions() {
  console.log("[Render] TopPredictions (Static)");

  return (
    <div className="w-full bg-slate-100 rounded-2xl p-4 shadow-sm border border-slate-200 mt-4">
      <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">
        Top-3 Predicciones
      </h4>
      <div className="flex flex-row justify-between gap-4">
        {[0, 1, 2].map((index) => (
          <div key={index} className="flex flex-col gap-1 flex-1">
            <div className="flex justify-between items-center text-xs">
              <span id={`pred-sign-${index}`} className="text-slate-700 font-bold capitalize">
                -
              </span>
              <span id={`pred-conf-${index}`} className="text-indigo-600 font-bold">
                0.0%
              </span>
            </div>
            <div className="w-full bg-slate-200 rounded-full h-1.5 overflow-hidden">
              <div
                id={`pred-bar-${index}`}
                className={`h-full rounded-full transition-all duration-300 ${
                  index === 0
                    ? "bg-indigo-500"
                    : index === 1
                      ? "bg-cyan-500"
                      : "bg-slate-500"
                }`}
                style={{ width: `0%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
