import { api } from "./client";

export interface Feedback {
  id: number;
  title: string;
  content: string;
  category: string;
  status: string;
  priority: string;
  submitted_by: string;
  submitted_by_role: string | null;
  project_id: number | null;
  entity_type: string | null;
  entity_id: number | null;
  admin_reply: string | null;
  replied_by: string | null;
  replied_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface FeedbackListResponse {
  total: number;
  items: Feedback[];
}

export interface CreateFeedbackRequest {
  title: string;
  content: string;
  category?: string;
  priority?: string;
  project_id?: number;
  entity_type?: string;
  entity_id?: number;
}

export interface UpdateFeedbackRequest {
  title?: string;
  content?: string;
  category?: string;
  status?: string;
  priority?: string;
  admin_reply?: string;
}

export interface FeedbackStats {
  total: number;
  by_status: Record<string, number>;
  by_category: Record<string, number>;
  by_submitter: { submitter: string; count: number }[];
}

export const feedbackApi = {
  list: (params?: { skip?: number; limit?: number; category?: string; status?: string; submitted_by?: string }) =>
    api.get<FeedbackListResponse>("/feedbacks", { params }).then((r) => r.data),
  get: (id: number) => api.get<Feedback>(`/feedbacks/${id}`).then((r) => r.data),
  create: (data: CreateFeedbackRequest) => api.post<Feedback>("/feedbacks", data).then((r) => r.data),
  update: (id: number, data: UpdateFeedbackRequest) => api.put<Feedback>(`/feedbacks/${id}`, data).then((r) => r.data),
  delete: (id: number) => api.delete(`/feedbacks/${id}`),
  stats: () => api.get<FeedbackStats>("/feedbacks/stats/summary").then((r) => r.data),
};
