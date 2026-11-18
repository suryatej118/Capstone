import { auth } from "../firebase";

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || ""
).replace(/\/$/, "");

export interface AnalyzeRequest {
  text: string;
  platform: string | null;
  save_report: boolean;
}

export interface AnalysisReason {
  rule_id: string;
  description: string;
  span: string;
  weight: number;
}

export interface HighlightedSpan {
  start: number;
  end: number;
  text: string;
}

export interface AnalyzeResponse {
  company_website: {
  status: string;
  verified: boolean;
  candidate_domain: string | null;
  reason?: string;
  website_url?: string;
  identity_evidence?: Record<string, unknown>;
};
  scan_id?: number | null;
  rule_score: number;
  ml_probability: number | null;
  final_score: number;
  risk_level: "Low" | "Medium" | "High" | string;
  confidence: number;
  reasons: AnalysisReason[];
  highlighted_spans: HighlightedSpan[];
  hiring_intent_score: number;
  hiring_intent_reasons: Record<string, unknown>[];
  suggested_templates: Record<string, unknown>[];
  critical_warnings?: CriticalWarning[];
}

export interface CriticalWarning {
  code: string;
  title: string;
  message: string;
  evidence: string;
}

async function authenticatedHeaders(
  headers: Record<string, string> = {}
) {
  const token = await auth.currentUser?.getIdToken();

  if (token) {
    return { ...headers, Authorization: `Bearer ${token}` };
  }

  return headers;
}

async function ensureSuccessful(
  response: Response,
  operation: string
) {
  if (response.ok) return;

  const errorBody = await response.text();
  const detail =
    response.status === 401
      ? "Please sign in again to continue."
      : response.status === 403
        ? "You are not authorized to access this resource."
        : errorBody || response.statusText;

  throw new Error(`${operation} failed (${response.status}): ${detail}`);
}

export async function analyzeJob(
  payload: AnalyzeRequest
): Promise<AnalyzeResponse> {
  const headers = await authenticatedHeaders({
    "Content-Type": "application/json",
  });
  const response = await fetch(`${API_BASE_URL}/analyze`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });

  await ensureSuccessful(response, "Analysis");

  return (await response.json()) as AnalyzeResponse;
}

export interface RecentScan {
  id: number;
  risk_level: "Low" | "Medium" | "High" | string;
  final_score: number;
  platform: string;
  created_at: string;
}

export interface DashboardStats {
  total_scans: number;
  high_risk: number;
  medium_risk: number;
  low_risk: number;
  recent_scans: RecentScan[];
}

export async function getDashboardStats(): Promise<DashboardStats> {
  const response = await fetch(
    `${API_BASE_URL}/dashboard/stats`,
    { headers: await authenticatedHeaders() }
  );

  await ensureSuccessful(response, "Dashboard request");

  return (await response.json()) as DashboardStats;
}

export interface ScanHistoryItem {
  id: number;
  platform: string;
  risk_level: "Low" | "Medium" | "High" | string;
  final_score: number;
  confidence: number;
  created_at: string;
  preview: string;
}

export interface ScanHistoryResponse {
  total: number;
  scans: ScanHistoryItem[];
}

export async function getScans(
  limit = 50,
  offset = 0
): Promise<ScanHistoryResponse> {
  const response = await fetch(
    `${API_BASE_URL}/scans?limit=${limit}&offset=${offset}`,
    { headers: await authenticatedHeaders() }
  );

  await ensureSuccessful(response, "Scan history request");

  return (await response.json()) as ScanHistoryResponse;
}

export interface ScanDetail {
  id: number;
  platform: string;
  submitted_text: string;
  rule_score: number;
  ml_probability: number | null;
  final_score: number;
  risk_level: string;
  confidence: number;
  hiring_intent_score: number;
  reasons: AnalysisReason[];
  highlighted_spans: HighlightedSpan[];
  hiring_intent_reasons: Record<string, unknown>[];
  suggested_templates: Record<string, unknown>[];
  created_at: string;
}

export async function getScanDetails(
  scanId: number
): Promise<ScanDetail> {
  const response = await fetch(
    `${API_BASE_URL}/scans/${scanId}`,
    { headers: await authenticatedHeaders() }
  );

  await ensureSuccessful(response, "Unable to retrieve scan");

  return (await response.json()) as ScanDetail;
}