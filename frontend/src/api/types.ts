export type ReportStatus =
  | "uploaded"
  | "ocr_running"
  | "parsing"
  | "explaining"
  | "completed"
  | "failed";

export interface StructuredResult {
  panel: string | null;
  test_name: string;
  value: string | null;
  unit: string | null;
  reference_range: string | null;
  status: "Low" | "Normal" | "High" | null;
  explanation: string | null;
  evidence: { reference_notes?: string } | null;
}

export interface Report {
  id: number;
  original_filename: string;
  status: ReportStatus;
  summary: string | null;
  error_message: string | null;
  created_at: string;
  results: StructuredResult[];
}

export interface ReportListItem {
  id: number;
  original_filename: string;
  status: ReportStatus;
  created_at: string;
}

export interface UserOut {
  id: number;
  email: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}
