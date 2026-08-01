import type { ReportStatus } from "../api/types";

const REPORT_STATUS_META: Record<ReportStatus, { label: string; className: string }> = {
  uploaded: { label: "Queued", className: "bg-slate-100 text-slate-700" },
  ocr_running: { label: "Reading report...", className: "bg-blue-100 text-blue-700" },
  parsing: { label: "Extracting values...", className: "bg-blue-100 text-blue-700" },
  explaining: { label: "Generating explanations...", className: "bg-blue-100 text-blue-700" },
  completed: { label: "Completed", className: "bg-emerald-100 text-emerald-700" },
  failed: { label: "Failed", className: "bg-red-100 text-red-700" },
};

export function ReportStatusBadge({ status }: { status: ReportStatus }) {
  const meta = REPORT_STATUS_META[status];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${meta.className}`}
    >
      {(status === "ocr_running" || status === "parsing" || status === "explaining") && (
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-current" />
      )}
      {meta.label}
    </span>
  );
}

const VALUE_STATUS_META: Record<string, string> = {
  Low: "bg-amber-100 text-amber-800",
  Normal: "bg-emerald-100 text-emerald-800",
  High: "bg-red-100 text-red-800",
};

export function ValueStatusPill({ status }: { status: string | null }) {
  if (!status) return null;
  const className = VALUE_STATUS_META[status] ?? "bg-slate-100 text-slate-700";
  return (
    <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold ${className}`}>
      {status}
    </span>
  );
}
