import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { ReportStatusBadge } from "../components/StatusBadge";
import { UploadDropzone } from "../components/UploadDropzone";
import { useState } from "react";
import type { ReportListItem } from "../api/types";

const IN_PROGRESS: ReportListItem["status"][] = ["uploaded", "ocr_running", "parsing", "explaining"];

export function Dashboard() {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [uploadError, setUploadError] = useState<string | null>(null);

  const { data: reports, isLoading } = useQuery({
    queryKey: ["reports"],
    queryFn: api.listReports,
    // keep list statuses live while anything is still processing
    refetchInterval: (query) => {
      const list = query.state.data;
      return list?.some((r) => IN_PROGRESS.includes(r.status)) ? 3000 : false;
    },
  });

  const uploadMutation = useMutation({
    mutationFn: api.uploadReport,
    onSuccess: (report) => {
      queryClient.invalidateQueries({ queryKey: ["reports"] });
      navigate(`/reports/${report.id}`);
    },
    onError: (err) => {
      setUploadError(err instanceof ApiError ? err.message : "Upload failed. Please try again.");
    },
  });

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-4 py-4">
          <h1 className="text-lg font-semibold text-slate-900">ReportLens</h1>
          <button
            onClick={logout}
            className="text-sm text-slate-500 transition-colors hover:text-slate-800"
          >
            Log out
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-3xl space-y-8 px-4 py-8">
        <section>
          <UploadDropzone
            disabled={uploadMutation.isPending}
            onFileSelected={(file) => {
              setUploadError(null);
              uploadMutation.mutate(file);
            }}
          />
          {uploadError && (
            <p className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
              {uploadError}
            </p>
          )}
        </section>

        <section>
          <h2 className="mb-3 text-sm font-medium text-slate-500">Your reports</h2>

          {isLoading && <p className="text-sm text-slate-400">Loading...</p>}

          {!isLoading && reports?.length === 0 && (
            <div className="rounded-2xl border border-dashed border-slate-200 bg-white py-12 text-center">
              <p className="text-sm text-slate-500">
                No reports yet. Upload one above to get started.
              </p>
            </div>
          )}

          {reports && reports.length > 0 && (
            <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
              {reports.map((report, i) => (
                <Link
                  key={report.id}
                  to={`/reports/${report.id}`}
                  className={`flex items-center justify-between px-4 py-3.5 transition-colors hover:bg-slate-50 ${
                    i !== reports.length - 1 ? "border-b border-slate-100" : ""
                  }`}
                >
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-slate-900">
                      {report.original_filename}
                    </p>
                    <p className="mt-0.5 text-xs text-slate-400">
                      {new Date(report.created_at).toLocaleString()}
                    </p>
                  </div>
                  <ReportStatusBadge status={report.status} />
                </Link>
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
