import type { ReportStatus } from "../api/types";

const STEPS: { status: ReportStatus; label: string }[] = [
  { status: "uploaded", label: "Uploaded" },
  { status: "ocr_running", label: "Reading report" },
  { status: "parsing", label: "Extracting values" },
  { status: "explaining", label: "Generating explanations" },
];

export function ProcessingSteps({ status }: { status: ReportStatus }) {
  if (status === "failed") return null;
  const currentIndex = STEPS.findIndex((s) => s.status === status);
  // once completed, every step (including the ones before "completed") is done
  const doneIndex = status === "completed" ? STEPS.length : currentIndex;

  return (
    <div className="w-full">
      <div className="flex items-center justify-between">
        {STEPS.map((step, i) => {
          const isDone = i < doneIndex;
          const isCurrent = i === doneIndex && status !== "completed";
          return (
            <div key={step.status} className="flex flex-1 flex-col items-center">
              <div className="flex w-full items-center">
                <div
                  className={`h-2.5 w-2.5 shrink-0 rounded-full ${
                    isDone
                      ? "bg-emerald-500"
                      : isCurrent
                        ? "animate-pulse bg-blue-500"
                        : "bg-slate-200"
                  }`}
                />
                {i < STEPS.length - 1 && (
                  <div
                    className={`h-0.5 flex-1 ${isDone ? "bg-emerald-500" : "bg-slate-200"}`}
                  />
                )}
              </div>
              <span
                className={`mt-2 text-center text-xs ${
                  isDone || isCurrent ? "font-medium text-slate-700" : "text-slate-400"
                }`}
              >
                {step.label}
              </span>
            </div>
          );
        })}
      </div>
      {status !== "completed" && (
        <p className="mt-6 text-center text-sm text-slate-500">
          This usually takes 1–3 minutes. Feel free to leave this page — your report keeps
          processing in the background.
        </p>
      )}
    </div>
  );
}
