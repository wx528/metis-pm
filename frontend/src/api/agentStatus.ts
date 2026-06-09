import { api } from "./client";

export interface AgentStatus {
  role: string;
  identity: string;
  last_active: string | null;
  status: "online" | "idle" | "offline";
  today_created: number;
  today_completed: number;
  today_reviewed: number;
  pending_tasks: number;
}

export interface PendingHandover {
  issue_id: number;
  from_role: string;
  to_role: string;
  title: string;
  created_at: string;
}

export interface AgentStatusResponse {
  agents: AgentStatus[];
  pending_handovers: PendingHandover[];
}

export const agentStatusApi = {
  get: (project_id?: number) =>
    api.get<AgentStatusResponse>("/dashboard/agents", {
      params: project_id ? { project_id } : undefined,
    }),
};
