import { api } from "./client";

export interface WorkflowStep {
  id: number;
  workflow_id: number;
  step_type: string;
  name: string | null;
  config: Record<string, any> | null;
  sort_order: number;
  timeout_seconds: number;
  on_failure: string;
}

export interface Workflow {
  id: number;
  project_id: number | null;
  name: string;
  description: string | null;
  trigger: string;
  trigger_config: Record<string, any> | null;
  status: string;
  created_by: string | null;
  created_at: string;
  updated_at: string;
  steps?: WorkflowStep[];
}

export interface WorkflowStepRun {
  id: number;
  run_id: number;
  step_id: number;
  status: string;
  result: Record<string, any> | null;
  error: string | null;
  retry_count: number;
  started_at: string | null;
  completed_at: string | null;
}

export interface WorkflowRun {
  id: number;
  workflow_id: number;
  triggered_by: string | null;
  status: string;
  current_step_index: number;
  context: Record<string, any> | null;
  error_message: string | null;
  started_at: string;
  completed_at: string | null;
  workflow_name?: string;
  step_runs?: WorkflowStepRun[];
}

export const workflowsApi = {
  list: (params?: Record<string, any>) =>
    api.get<Workflow[]>("/workflows", { params }).then((r) => r.data),

  get: (id: number) =>
    api.get<Workflow>(`/workflows/${id}`).then((r) => r.data),

  create: (data: Partial<Workflow> & { steps?: any[] }) =>
    api.post<Workflow>("/workflows", data).then((r) => r.data),

  update: (id: number, data: Partial<Workflow>) =>
    api.put<Workflow>(`/workflows/${id}`, data).then((r) => r.data),

  delete: (id: number) =>
    api.delete(`/workflows/${id}`),

  listRuns: (params?: Record<string, any>) =>
    api.get<WorkflowRun[]>("/workflows/runs", { params }).then((r) => r.data),

  trigger: (id: number) =>
    api.post<WorkflowRun>(`/workflows/${id}/trigger`).then((r) => r.data),

  resume: (runId: number, approved: boolean = true) =>
    api.post<WorkflowRun>(`/workflows/runs/${runId}/resume`, null, { params: { approved } }).then((r) => r.data),

  getRun: (runId: number) =>
    api.get<WorkflowRun>(`/workflows/runs/${runId}`).then((r) => r.data),
};
