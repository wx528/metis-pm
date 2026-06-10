import { useQuery } from "@tanstack/react-query";
import { issueKeys, fetchIssuesData } from "../queries/issueQueries";

export function useIssues(
  projectId: number | undefined,
  filters: Record<string, any>,
  page: number,
  pageSize: number,
  sortBy: string
) {
  return useQuery({
    queryKey: issueKeys.list(projectId, filters, page, pageSize, sortBy),
    queryFn: () => fetchIssuesData(projectId, filters, page, pageSize, sortBy),
    enabled: !!projectId,
  });
}
