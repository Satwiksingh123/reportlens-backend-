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
          {/* Measured, not guessed: each biomarker gets its own local-LLM explanation, which
              runs ~30-60s on CPU. A single-analyte report finishes in about a minute; a full
              panel took 4-10 minutes on the machine this was developed on. Promising "1-3
              minutes" for all of them just makes a working system look broken. */}
          A short report takes a minute or two; a full panel can take several minutes, since
          every value is explained by a model running on your own hardware. You can leave
          this page — processing continues in the background.
        </p>
      )}
    </div>
  );
}
