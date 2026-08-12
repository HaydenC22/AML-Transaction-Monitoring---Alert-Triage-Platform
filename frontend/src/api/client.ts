const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export interface AlertSummary {
  alert_id: number;
  transaction_key: string;
  transaction_type: string;
  amount: number;
  origin_account_nk: string;
  severity: "low" | "medium" | "high" | "critical";
  composite_score: number;
  ml_anomaly_score: number;
  is_fraud_label: boolean;
  created_at: string;
  status: "open" | "closed";
  rule_flags: string[];
}

export interface AlertListResponse {
  items: AlertSummary[];
  total: number;
  page: number;
  page_size: number;
}

export interface TransactionContext {
  transaction_key: string;
  day_offset: number;
  transaction_type: string;
  amount: number;
}

export interface Disposition {
  disposition_id: number;
  analyst_id: string;
  outcome: "true_positive" | "false_positive";
  rationale_notes: string;
  dispositioned_at: string;
}

export interface CaseNote {
  note_id: number;
  author: string;
  note_text: string;
  created_at: string;
}

export interface AlertDetail extends AlertSummary {
  origin_geography_key: string | null;
  dest_geography_key: string | null;
  account_history: TransactionContext[];
  disposition: Disposition | null;
  notes: CaseNote[];
}

export interface OverviewMetrics {
  alert_volume_by_day: { day_offset: number; alert_count: number }[];
  fp_rate_trend: { day: string; fp_rate_pct: number; dispositions: number }[];
  severity_breakdown: { severity: string; alert_count: number; true_positive_count: number }[];
  analyst_throughput_by_day: { day: string; dispositions: number }[];
  latest_pipeline_run: {
    run_id: number;
    run_at: string;
    rows_processed: number;
    alerts_generated: number;
    precision_at_threshold: number;
    recall_at_threshold: number;
    fp_rate_at_threshold: number;
    runtime_seconds: number;
    ge_status: string;
  } | null;
}

export interface TimelinePoint {
  day_offset: number;
  transaction_count: number;
  total_amount: number;
}

export interface ThresholdPoint {
  threshold: number;
  alerts_flagged: number;
  precision: number;
  recall: number;
  fp_rate: number;
}

export interface RuleVolume {
  rule_name: string;
  alert_count: number;
  true_positive_count: number;
}

export interface ThresholdRecommendation {
  current_threshold: number;
  recommended_threshold: number | null;
  dispositions_considered: number;
  computed_at: string | null;
}

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    throw new ApiError(resp.status, body.detail ?? resp.statusText);
  }
  if (resp.status === 204) return undefined as T;
  return resp.json() as Promise<T>;
}

export interface AlertListParams {
  status?: "open" | "closed";
  severity?: "low" | "medium" | "high" | "critical";
  rule?: string;
  page?: number;
  page_size?: number;
}

export const api = {
  listAlerts(params: AlertListParams = {}): Promise<AlertListResponse> {
    const search = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== "") search.set(key, String(value));
    });
    return request(`/alerts?${search.toString()}`);
  },
  getAlert(alertId: number): Promise<AlertDetail> {
    return request(`/alerts/${alertId}`);
  },
  dispositionAlert(
    alertId: number,
    payload: { analyst_id: string; outcome: "true_positive" | "false_positive"; rationale_notes: string }
  ): Promise<Disposition> {
    return request(`/alerts/${alertId}/disposition`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  addNote(alertId: number, payload: { author: string; note_text: string }): Promise<CaseNote> {
    return request(`/alerts/${alertId}/notes`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  getOverview(): Promise<OverviewMetrics> {
    return request("/metrics/overview");
  },
  getCaseTimeline(alertId: number): Promise<TimelinePoint[]> {
    return request(`/metrics/cases/${alertId}/timeline`);
  },
  getThresholdCurve(): Promise<ThresholdPoint[]> {
    return request("/metrics/threshold-curve");
  },
  getRuleVolume(): Promise<RuleVolume[]> {
    return request("/metrics/rule-volume");
  },
  getThresholdRecommendation(): Promise<ThresholdRecommendation> {
    return request("/metrics/threshold-recommendation");
  },
};

export { ApiError };
