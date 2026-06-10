import { dashboardApi } from "../api/dashboard";
import { statsApi } from "../api/stats";
import type { DashboardData } from "../api/dashboard";
import type { AgentProductivity, PlanCompletion } from "../api/stats";

export const dashboardKeys = {
  all: ["dashboard"] as const,
  detail: (projectId: number, period: string) =>
    ["dashboard", "detail", projectId, period] as const,
};

export interface DashboardQueryResult {
  dashboard: DashboardData;
  productivity: AgentProductivity;
  planCompletion: PlanCompletion;
}

export async function fetchDashboardData(
  projectId: number,
  period: string
): Promise<DashboardQueryResult> {
  const [dashboardRes, prodRes, planRes] = await Promise.all([
    dashboardApi.get({ project_id: projectId }),
    statsApi.agentProductivity(projectId, period),
    statsApi.planCompletion(projectId),
  ]);

  return {
    dashboard: dashboardRes.data,
    productivity: prodRes,
    planCompletion: planRes,
  };
}
