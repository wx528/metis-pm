import { api } from "./client";

export interface Project {
  id: number;
  name: string;
  slug: string;
  description: string | null;
  repo_url: string | null;
  status: string;
  owner: string | null;
  default_milestone_id: number | null;
  created_at: string;
  updated_at: string;
  issue_count?: number;
  open_issue_count?: number;
  plan_count?: number;
  milestone_count?: number;
  server_count?: number;
}

export interface ProjectCreate {
  name: string;
  slug: string;
  description?: string;
  repo_url?: string;
  status?: string;
  owner?: string;
}

export interface ProjectUpdate {
  name?: string;
  description?: string;
  repo_url?: string;
  status?: string;
  owner?: string;
}

export const projectsApi = {
  list: () => api.get<Project[]>("/projects").then((r) => r.data),
  get: (slug: string) => api.get<Project>(`/projects/${slug}`).then((r) => r.data),
  create: (data: ProjectCreate) => api.post<Project>("/projects", data).then((r) => r.data),
  update: (slug: string, data: ProjectUpdate) => api.put<Project>(`/projects/${slug}`, data).then((r) => r.data),
  delete: (slug: string) => api.delete(`/projects/${slug}`),
};
