const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || ""
).replace(/\/$/, "");

export interface AnalyzeRequest {
  text: string;
  platform: string | null;
  requester_id: string;
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
}

export async function analyzeJob(
  payload: AnalyzeRequest
): Promise<AnalyzeResponse> {
  const response = await fetch(`${API_BASE_URL}/analyze`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(
      `Analysis failed (${response.status}): ${errorBody || response.statusText}`
    );
  }

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
  const response = await fetch(`${API_BASE_URL}/dashboard/stats`);

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(
      `Dashboard request failed (${response.status}): ${
        errorBody || response.statusText
      }`
    );
  }

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
    `${API_BASE_URL}/scans?limit=${limit}&offset=${offset}`
  );

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(
      `Scan history request failed (${response.status}): ${
        errorBody || response.statusText
      }`
    );
  }

  return (await response.json()) as ScanHistoryResponse;
}

export interface ScanDetail {
  id: number;
  requester_id: string;
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
  const response = await fetch(`${API_BASE_URL}/scans/${scanId}`);

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(
      `Unable to retrieve scan (${response.status}): ${
        errorBody || response.statusText
      }`
    );
  }

  return (await response.json()) as ScanDetail;
}