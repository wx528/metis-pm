import { api } from "./client";

export interface RiskAlert {
  id: number;
  title: string;
  description?: string;
  level: string;
  source: string;
  status: string;
  suggested_action?: string;
  resolved_by?: string;
  resolved_at?: string;
  project_id?: number;
  created_by?: string;
  created_at: string;
  updated_at: string;
}

export interface RiskAlertListResponse {
  total: number;
  items: RiskAlert[];
}

export interface RiskAlertCreate {
  title: string;
  description?: string;
  level?: string;
  source?: string;
  suggested_action?: string;
  project_id?: number;
}

export interface RiskAlertUpdate {
  title?: string;
  description?: string;
  level?: string;
  status?: string;
  suggested_action?: string;
}

export const riskAlertsApi = {
  list: (params?: Record<string, any>) =>
    api.get<RiskAlertListResponse>("/risk-alerts", { params }),
  get: (id: number) =>
    api.get<RiskAlert>(`/risk-alerts/${id}`),
  create: (data: RiskAlertCreate) =>
    api.post<RiskAlert>("/risk-alerts", data),
  update: (id: number, data: RiskAlertUpdate) =>
    api.put<RiskAlert>(`/risk-alerts/${id}`, data),
  resolve: (id: number) =>
    api.post<RiskAlert>(`/risk-alerts/${id}/resolve`),
  remove: (id: number) =>
    api.delete(`/risk-alerts/${id}`),
};
