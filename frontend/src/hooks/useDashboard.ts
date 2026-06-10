import { useQuery } from "@tanstack/react-query";
import { dashboardKeys, fetchDashboardData } from "../queries/dashboardQueries";

export function useDashboard(projectId: number | undefined, period: string) {
  return useQuery({
    queryKey: dashboardKeys.detail(projectId ?? 0, period),
    queryFn: () => fetchDashboardData(projectId!, period),
    enabled: !!projectId,
  });
}
