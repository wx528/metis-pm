import { api } from "./client";

export interface AgentProductivity {
  period: string;
  agents: { actor: string; created: number; completed: number }[];
}

export interface IssueResolution {
  period: string;
  overall: {
    count: number;
    avg_hours: number;
    median_hours: number;
    p90_hours: number;
  };
  by_type: {
    issue_type: string;
    count: number;
    avg_hours: number;
    median_hours: number;
    p90_hours: number;
  }[];
}

export interface PlanCompletion {
  total_plans: number;
  overall_completion_rate: number;
  total_items: number;
  total_done_items: number;
  by_status: Record<string, number>;
  plans: {
    id: number;
    title: string;
    status: string;
    total_items: number;
    done_items: number;
    completion_rate: number;
  }[];
}

export interface AgentActivity {
  days: number;
  actors: string[];
  daily_activity: Record<string, number>[];
  action_distribution: Record<string, Record<string, number>>;
}

export const statsApi = {
  agentProductivity: (projectId: number, period: string = "all") =>
    api
      .get<AgentProductivity>("/stats/agent-productivity", {
        params: { project_id: projectId, period },
      })
      .then((r) => r.data),

  issueResolution: (projectId: number, period: string = "all") =>
    api
      .get<IssueResolution>("/stats/issue-resolution", {
        params: { project_id: projectId, period },
      })
      .then((r) => r.data),

  planCompletion: (projectId: number) =>
    api
      .get<PlanCompletion>("/stats/plan-completion", {
        params: { project_id: projectId },
      })
      .then((r) => r.data),

  agentActivity: (projectId: number, days: number = 30) =>
    api
      .get<AgentActivity>("/stats/agent-activity", {
        params: { project_id: projectId, days },
      })
      .then((r) => r.data),
};
