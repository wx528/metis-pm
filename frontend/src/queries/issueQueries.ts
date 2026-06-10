import { issuesApi } from "../api/issues";
import { milestonesApi } from "../api/milestones";
import type { Issue, Milestone } from "../api";

export const issueKeys = {
  all: ["issues"] as const,
  list: (projectId: number | undefined, filters: Record<string, any>, page: number, pageSize: number, sortBy: string) =>
    ["issues", "list", projectId, filters, page, pageSize, sortBy] as const,
};

export interface IssuesQueryResult {
  items: Issue[];
  total: number;
  milestones: Milestone[];
}

export async function fetchIssuesData(
  projectId: number | undefined,
  filters: Record<string, any>,
  page: number,
  pageSize: number,
  sortBy: string
): Promise<IssuesQueryResult> {
  const params: Record<string, any> = { ...filters, skip: (page - 1) * pageSize, limit: pageSize, sort_by: sortBy };
  if (projectId) params.project_id = projectId;

  const [issuesRes, milestonesRes] = await Promise.all([
    issuesApi.list(params),
    milestonesApi.list(projectId ? { project_id: projectId } : {}),
  ]);

  return {
    items: issuesRes.data.items,
    total: issuesRes.data.total,
    milestones: milestonesRes.data,
  };
}
