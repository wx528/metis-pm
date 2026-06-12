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

export interface CollaborationFlowItem {
  issue_id: number;
  actor: string;
  from_role: string;
  to_role: string;
  action: string;
  old_status: string | null;
  new_status: string | null;
  created_at: string;
}

export interface ActivityStreamItem {
  id: number;
  actor: string;
  role: string;
  entity_type: string;
  entity_id: number;
  action: string;
  old_value: Record<string, unknown> | null;
  new_value: Record<string, unknown> | null;
  created_at: string;
}

export interface WorkloadIssue {
  id: number;
  title: string;
  status: string;
  priority: string;
  assignee: string | null;
}

export interface AgentStatusResponse {
  agents: AgentStatus[];
  pending_handovers: PendingHandover[];
  collaboration_flow?: CollaborationFlowItem[];
  activity_stream?: ActivityStreamItem[];
  workload?: Record<string, WorkloadIssue[]>;
}

export const agentStatusApi = {
  get: (project_id?: number, options?: { include_flow?: boolean; include_activity?: boolean; activity_limit?: number }) =>
    api.get<AgentStatusResponse>("/dashboard/agents", {
      params: {
        ...(project_id ? { project_id } : {}),
        ...(options?.include_flow ? { include_flow: true } : {}),
        ...(options?.include_activity ? { include_activity: true } : {}),
        ...(options?.activity_limit ? { activity_limit: options.activity_limit } : {}),
      },
    }),
};
