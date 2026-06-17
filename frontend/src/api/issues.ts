import { api } from "./client";

export interface Issue {
  id: number; project_id?: number; title: string; description?: string;
  issue_type: string; status: string; priority: string;
  assignee_role?: string; source_role?: string;
  created_at: string; updated_at: string;
}
export interface IssueListResponse { total: number; items: Issue[]; }
export interface IssueCreate {
  title: string; description?: string; issue_type?: string;
  priority?: string; assignee_role?: string; source_role?: string; project_id?: number;
}
export interface IssueUpdate {
  title?: string; description?: string; issue_type?: string;
  status?: string; priority?: string; assignee_role?: string;
}
export interface Comment { id: number; issue_id: number; author_role?: string; content: string; created_at: string; }
export interface IssueWithComments extends Issue { comments: Comment[]; }
export interface CommentCreate { content: string; author_role?: string; }
export const issuesApi = {
  list: (params?: Record<string, any>) => api.get<IssueListResponse>("/issues", { params }),
  get: (id: number) => api.get<IssueWithComments>(`/issues/${id}`),
  create: (data: IssueCreate) => api.post<Issue>("/issues", data),
  update: (id: number, data: IssueUpdate) => api.put<Issue>(`/issues/${id}`, data),
  remove: (id: number) => api.delete(`/issues/${id}`),
  addComment: (issueId: number, data: CommentCreate) => api.post<Comment>(`/issues/${issueId}/comments`, data),
};
