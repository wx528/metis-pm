import { api } from "./client";

export interface Issue {
  id: number;
  title: string;
  description?: string;
  issue_type: string;
  status: string;
  priority: string;
  source: string;
  assignee?: string;
  labels?: string;
  milestone_id?: number;
  deferred_to_milestone_id?: number;
  deferred_reason?: string;
  parent_id?: number;
  created_at: string;
  updated_at: string;
  closed_at?: string;
}

export interface IssueListResponse {
  total: number;
  items: Issue[];
}

export interface IssueCreate {
  title: string;
  description?: string;
  issue_type?: string;
  status?: string;
  priority?: string;
  source?: string;
  assignee?: string;
  labels?: string;
  milestone_id?: number;
}

export interface IssueUpdate {
  title?: string;
  description?: string;
  issue_type?: string;
  status?: string;
  priority?: string;
  assignee?: string;
  labels?: string;
  milestone_id?: number;
}

export interface Comment {
  id: number;
  issue_id: number;
  author?: string;
  content: string;
  created_at: string;
}

export interface IssueWithComments extends Issue {
  comments: Comment[];
}

export interface CommentCreate {
  content: string;
  author?: string;
}

export const issuesApi = {
  list: (params?: Record<string, any>) =>
    api.get<IssueListResponse>("/issues", { params }),
  get: (id: number) => api.get<IssueWithComments>(`/issues/${id}`),
  create: (data: IssueCreate) => api.post<Issue>("/issues", data),
  update: (id: number, data: IssueUpdate) => api.put<Issue>(`/issues/${id}`, data),
  remove: (id: number) => api.delete(`/issues/${id}`),
  defer: (id: number, milestoneId: number, reason?: string) =>
    api.post<Issue>(`/issues/${id}/defer`, null, {
      params: { deferred_to_milestone_id: milestoneId, deferred_reason: reason },
    }),
  addComment: (issueId: number, data: CommentCreate) =>
    api.post<Comment>(`/issues/${issueId}/comments`, data),
};
