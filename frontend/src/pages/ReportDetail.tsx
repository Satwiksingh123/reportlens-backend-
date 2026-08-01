import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import { ProcessingSteps } from "../components/ProcessingSteps";
import { ResultCard } from "../components/ResultCard";

const TERMINAL = new Set(["completed", "failed"]);

export function ReportDetail() {
  const { id } = useParams<{ id: string }>();
  const reportId = Number(id);

  const { data: report, isLoading, error } = useQuery({
    queryKey: ["report", reportId],
    queryFn: () => api.getReport(reportId),
    refetchInterval: (query) => (TERMINAL.has(query.state.data?.status ?? "") ? false : 2500),
    enabled: Number.isFinite(reportId),
  });

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-3xl items-center gap-3 px-4 py-4">
          <Link to="/" className="text-sm text-slate-500 hover:text-slate-800">
            ← Reports
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-3xl space-y-6 px-4 py-8">
        {isLoading && <p className="text-sm text-slate-400">Loading...</p>}

        {error && (
          <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
            Couldn't load this report. It may not exist, or may belong to another account.
          </p>
        )}

        {report && (
          <>
            <div>
              <h1 className="text-xl font-semibold text-slate-900">
                {report.original_filename}
              </h1>
              <p className="mt-1 text-xs text-slate-400">
                Uploaded {new Date(report.created_at).toLocaleString()}
              </p>
            </div>

            {report.status !== "completed" && report.status !== "failed" && (
              <div className="rounded-2xl border border-slate-200 bg-white p-6">
                <ProcessingSteps status={report.status} />
              </div>
            )}

            {report.status === "failed" && (
              <div className="rounded-2xl border border-red-200 bg-red-50 p-6">
                <p className="text-sm font-medium text-red-800">
                  Something went wrong while processing this report.
                </p>
                {report.error_message && (
                  <p className="mt-1 text-sm text-red-700">{report.error_message}</p>
                )}
                <p className="mt-3 text-sm text-red-700">
                  Try uploading the file again, or a clearer copy of it.
                </p>
              </div>
            )}

            {report.status === "completed" && (
              <>
                {report.summary && (
                  <div className="rounded-2xl border border-blue-100 bg-blue-50 p-5">
                    <h2 className="mb-1 text-sm font-semibold text-blue-900">Summary</h2>
                    <p className="text-sm leading-relaxed text-blue-900">{report.summary}</p>
                  </div>
                )}

                {report.results.length === 0 ? (
                  <div className="rounded-2xl border border-dashed border-slate-200 bg-white py-10 text-center">
                    <p className="text-sm text-slate-500">
                      We couldn't extract any recognized values from this report. Try a
                      clearer scan or photo, or a different file.
                    </p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {report.results.map((result, i) => (
                      <ResultCard key={`${result.test_name}-${i}`} result={result} />
                    ))}
                  </div>
                )}
              </>
            )}
          </>
        )}
      </main>
    </div>
  );
}
