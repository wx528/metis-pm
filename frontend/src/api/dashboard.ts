import { api } from "./client";

export interface DashboardData {
  issues: {
    total: number;
    p0: number;
    p1: number;
    open: number;
    in_progress: number;
    deferred: number;
    ai_agent: number;
  };
  plans: {
    total: number;
    pending_approval: number;
    active: number;
  };
  servers: {
    total: number;
    active: number;
    maintenance: number;
    offline: number;
  };
  recent_activities: {
    id: number;
    entity_type: string;
    entity_id: number;
    action: string;
    actor: string;
    created_at: string;
  }[];
  pending_plans: {
    id: number;
    title: string;
    description?: string;
    proposed_by: string;
    created_at: string;
  }[];
  recent_issues: {
    id: number;
    title: string;
    priority: string;
    status: string;
    source: string;
    created_at: string;
  }[];
}

export const dashboardApi = {
  get: () => api.get<DashboardData>("/dashboard"),
};
