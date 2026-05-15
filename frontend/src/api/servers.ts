import { api } from "./client";

export interface Server {
  id: number;
  name: string;
  description?: string;
  ip_address?: string;
  port?: number;
  username?: string;
  has_password: boolean;
  has_ssh_key: boolean;
  server_type: string;
  status: string;
  environment: string;
  labels?: string;
  last_checked_at?: string;
  created_at: string;
  updated_at: string;
}

export interface ServerCreate {
  name: string;
  description?: string;
  ip_address?: string;
  port?: number;
  username?: string;
  password?: string;
  ssh_key?: string;
  server_type?: string;
  status?: string;
  environment?: string;
  labels?: string;
}

export interface ServerUpdate {
  name?: string;
  description?: string;
  ip_address?: string;
  port?: number;
  username?: string;
  password?: string;
  ssh_key?: string;
  server_type?: string;
  status?: string;
  environment?: string;
  labels?: string;
}

export interface ServerCredentials {
  id: number;
  name: string;
  ip_address?: string;
  port?: number;
  username?: string;
  password?: string;
  ssh_key?: string;
}

export const serversApi = {
  list: (params?: Record<string, any>) => api.get<Server[]>("/servers", { params }),
  get: (id: number) => api.get<Server>(`/servers/${id}`),
  create: (data: ServerCreate) => api.post<Server>("/servers", data),
  update: (id: number, data: ServerUpdate) => api.put<Server>(`/servers/${id}`, data),
  remove: (id: number) => api.delete(`/servers/${id}`),
  getCredentials: (id: number) => api.get<ServerCredentials>(`/servers/${id}/credentials`),
};
