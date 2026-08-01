import { useState } from "react";
import type { StructuredResult } from "../api/types";
import { ValueStatusPill } from "./StatusBadge";

export function ResultCard({ result }: { result: StructuredResult }) {
  const [showEvidence, setShowEvidence] = useState(false);
  const notes = result.evidence?.reference_notes;

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          {result.panel && (
            <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
              {result.panel}
            </p>
          )}
          <h3 className="text-base font-semibold text-slate-900">{result.test_name}</h3>
        </div>
        <ValueStatusPill status={result.status} />
      </div>

      <div className="mt-2 flex flex-wrap items-baseline gap-x-4 gap-y-1 text-sm">
        {result.value && (
          <span className="font-medium text-slate-900">
            {result.value} {result.unit ?? ""}
          </span>
        )}
        {result.reference_range && (
          <span className="text-slate-400">Reference: {result.reference_range}</span>
        )}
      </div>

      {result.explanation && (
        <p className="mt-3 text-sm leading-relaxed text-slate-600">{result.explanation}</p>
      )}

      {notes && (
        <div className="mt-3">
          <button
            onClick={() => setShowEvidence((v) => !v)}
            className="text-xs font-medium text-blue-600 hover:text-blue-800"
          >
            {showEvidence ? "Hide source" : "Show source"}
          </button>
          {showEvidence && (
            <p className="mt-2 rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-500">
              {notes}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
