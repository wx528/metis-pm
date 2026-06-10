import { useQuery } from "@tanstack/react-query";
import { workflowKeys, fetchWorkflowsData } from "../queries/workflowQueries";

export function useWorkflows(projectId: number | undefined) {
  return useQuery({
    queryKey: workflowKeys.list(projectId),
    queryFn: () => fetchWorkflowsData(projectId),
    enabled: !!projectId,
  });
}
