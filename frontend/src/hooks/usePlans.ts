import { useQuery } from "@tanstack/react-query";
import { planKeys, fetchPlans } from "../queries/planQueries";

export function usePlans(projectId: number | undefined) {
  return useQuery({
    queryKey: planKeys.list(projectId),
    queryFn: () => fetchPlans(projectId),
    enabled: !!projectId,
  });
}
