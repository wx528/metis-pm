import { api } from "./client";

export interface ProjectRegistration {
  id: number;
  name: string;
  path: string;
  description: string | null;
  tech_stack: string | null;
  repo_url: string | null;
  language: string | null;
  framework: string | null;
  status: string;
  notes: string | null;
  registered_by: string | null;
  last_scanned_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectRegistrationCreate {
  name: string;
  path: string;
  description?: string;
  tech_stack?: string;
  repo_url?: string;
  language?: string;
  framework?: string;
  status?: string;
  notes?: string;
}

export interface ProjectRegistrationUpdate {
  name?: string;
  path?: string;
  description?: string;
  tech_stack?: string;
  repo_url?: string;
  language?: string;
  framework?: string;
  status?: string;
  notes?: string;
}

export interface ProjectRegistrationListResponse {
  total: number;
  items: ProjectRegistration[];
}

export const projectRegistrationsApi = {
  list: (params?: Record<string, any>) =>
    api.get<ProjectRegistrationListResponse>("/project-registrations", { params }).then((r) => r.data),
  get: (id: number) =>
    api.get<ProjectRegistration>(`/project-registrations/${id}`).then((r) => r.data),
  create: (data: ProjectRegistrationCreate) =>
    api.post<ProjectRegistration>("/project-registrations", data).then((r) => r.data),
  update: (id: number, data: ProjectRegistrationUpdate) =>
    api.put<ProjectRegistration>(`/project-registrations/${id}`, data).then((r) => r.data),
  delete: (id: number) =>
    api.delete(`/project-registrations/${id}`),
};
