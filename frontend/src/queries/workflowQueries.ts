import { workflowsApi } from "../api/workflows";
import type { Workflow, WorkflowRun } from "../api/workflows";

export const workflowKeys = {
  all: ["workflows"] as const,
  list: (projectId: number | undefined) => ["workflows", "list", projectId] as const,
  runs: ["workflowRuns"] as const,
};

export interface WorkflowsQueryResult {
  workflows: Workflow[];
  runs: WorkflowRun[];
}

export async function fetchWorkflowsData(projectId: number | undefined): Promise<WorkflowsQueryResult> {
  if (!projectId) return { workflows: [], runs: [] };

  const [wfRes, runRes] = await Promise.all([
    workflowsApi.list({ project_id: projectId }),
    workflowsApi.listRuns({ limit: 20 }),
  ]);

  const runs = runRes.filter((r) => {
    const wf = wfRes.find((w) => w.id === r.workflow_id);
    return wf !== undefined;
  });

  return { workflows: wfRes, runs };
}
