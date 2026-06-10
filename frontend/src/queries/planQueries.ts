import { plansApi } from "../api/plans";
import type { Plan } from "../api";

export const planKeys = {
  all: ["plans"] as const,
  list: (projectId: number | undefined) => ["plans", "list", projectId] as const,
};

export async function fetchPlans(projectId: number | undefined): Promise<Plan[]> {
  const params: Record<string, any> = {};
  if (projectId) params.project_id = projectId;
  const res = await plansApi.list(params);
  return res.data;
}
