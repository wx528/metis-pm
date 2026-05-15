import { api } from "./client";

export interface Milestone {
  id: number;
  title: string;
  description?: string;
  phase?: string;
  status: string;
  due_date?: string;
  created_at: string;
  updated_at: string;
}

export interface MilestoneWithStats extends Milestone {
  total_issues: number;
  open_issues: number;
  closed_issues: number;
  deferred_issues: number;
}

export const milestonesApi = {
  list: (params?: Record<string, any>) => api.get<MilestoneWithStats[]>("/milestones", { params }),
  get: (id: number) => api.get<MilestoneWithStats>(`/milestones/${id}`),
  create: (data: Partial<Milestone>) => api.post<Milestone>("/milestones", data),
  update: (id: number, data: Partial<Milestone>) => api.put<Milestone>(`/milestones/${id}`, data),
  remove: (id: number) => api.delete(`/milestones/${id}`),
};
