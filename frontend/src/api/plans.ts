import { api } from "./client";

export interface PlanItem {
  id: number; plan_id: number; title: string; description?: string;
  status: string; sort_order: number; completed_by?: string;
  completed_at?: string; created_at: string; updated_at: string;
}
export interface Plan {
  id: number; project_id?: number; title: string; description?: string;
  status: string; proposed_by?: string; approved_by?: string;
  approved_at?: string; reject_reason?: string;
  created_at: string; updated_at: string;
  plan_items?: PlanItem[]; item_count?: number; item_done_count?: number;
}
export const plansApi = {
  list: (params?: Record<string, any>) => api.get<Plan[]>("/plans", { params }),
  get: (id: number) => api.get<Plan>(`/plans/${id}`),
  create: (data: Partial<Plan>) => api.post<Plan>("/plans", data),
  update: (id: number, data: Partial<Plan>) => api.put<Plan>(`/plans/${id}`, data),
  remove: (id: number) => api.delete(`/plans/${id}`),
  approve: (id: number) => api.post<Plan>(`/plans/${id}/approve`),
  reject: (id: number, reason?: string) => api.post<Plan>(`/plans/${id}/reject`, { reason }),
  listItems: (planId: number) => api.get<PlanItem[]>(`/plans/${planId}/items`),
  createItem: (planId: number, data: Partial<PlanItem>) => api.post<PlanItem>(`/plans/${planId}/items`, data),
  updateItem: (planId: number, itemId: number, data: Partial<PlanItem>) => api.put<PlanItem>(`/plans/${planId}/items/${itemId}`, data),
  removeItem: (planId: number, itemId: number) => api.delete(`/plans/${planId}/items/${itemId}`),
};
