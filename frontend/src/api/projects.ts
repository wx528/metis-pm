import { api } from "./client";

export interface Project { id: number; name: string; slug: string; description?: string; status: string; created_at: string; updated_at: string; }
export interface ProjectWithStats extends Project { issue_count: number; open_issue_count: number; plan_count: number; }
export interface ProjectCreate { name: string; slug: string; description?: string; }
export interface ProjectUpdate { name?: string; slug?: string; description?: string; status?: string; }
export const projectsApi = {
  list: (params?: Record<string, any>) => api.get<ProjectWithStats[]>("/projects", { params }),
  get: (slug: string) => api.get<ProjectWithStats>(`/projects/${slug}`),
  create: (data: ProjectCreate) => api.post<Project>("/projects", data),
  update: (slug: string, data: ProjectUpdate) => api.put<Project>(`/projects/${slug}`, data),
  remove: (slug: string) => api.delete(`/projects/${slug}`),
};
