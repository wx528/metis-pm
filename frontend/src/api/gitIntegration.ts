import { api } from "./client";

export interface GitIntegration {
  id: number;
  project_id: number;
  repo_url: string;
  platform: "github" | "gitea" | "forgejo";
  webhook_url: string | null;
  auto_close_issue: boolean;
  auto_link_pr: boolean;
  auto_create_issue: boolean;
  subscribed_events: string[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface GitIntegrationCreate {
  project_id: number;
  repo_url: string;
  platform: "github" | "gitea" | "forgejo";
  webhook_secret: string;
  auto_close_issue?: boolean;
  auto_link_pr?: boolean;
  subscribed_events?: string[];
}

export interface GitIntegrationUpdate {
  repo_url?: string;
  webhook_secret?: string;
  auto_close_issue?: boolean;
  auto_link_pr?: boolean;
  subscribed_events?: string[];
  is_active?: boolean;
}

export interface CommitLink {
  id: number;
  issue_id: number;
  commit_hash: string;
  commit_short: string;
  commit_message: string;
  commit_url: string | null;
  author: string;
  action: string;
  branch: string | null;
  committed_at: string;
  created_at: string;
}

export interface PRPlanLink {
  id: number;
  pr_number: number;
  pr_title: string;
  pr_url: string | null;
  pr_status: string;
  plan_id: number;
  author: string | null;
  merged_at: string | null;
  created_at: string;
}

export const gitIntegrationApi = {
  list: (projectId?: number) =>
    api.get<GitIntegration[]>("/git-integrations", {
      params: projectId ? { project_id: projectId } : undefined,
    }),

  create: (data: GitIntegrationCreate) =>
    api.post<GitIntegration>("/git-integrations", data),

  update: (id: number, data: GitIntegrationUpdate) =>
    api.put<GitIntegration>(`/git-integrations/${id}`, data),

  delete: (id: number) => api.delete(`/git-integrations/${id}`),

  regenerateSecret: (id: number) =>
    api.post<{ secret: string }>(`/git-integrations/${id}/regenerate-secret`),
};

export const commitLinkApi = {
  getByIssue: (issueId: number) =>
    api.get<CommitLink[]>(`/issues/${issueId}/commits`),
};

export const prLinkApi = {
  getByPlan: (planId: number) =>
    api.get<PRPlanLink[]>(`/plans/${planId}/prs`),
};
