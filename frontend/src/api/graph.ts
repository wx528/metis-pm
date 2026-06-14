import { api } from "./client";

export interface GraphNode {
  id: string;
  type: "milestone" | "issue";
  title: string;
  issue_id?: number;
  priority?: string;
  status?: string;
  issue_type?: string;
  labels?: string[];
  milestone_id?: number;
  parent_id?: number;
  size: number;
  color: string;
  opacity: number;
}

export interface GraphEdge {
  source: string;
  target: string;
}

export interface GraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
  labels: Record<string, string>;
}

export interface GraphParams {
  status?: string;
  issue_type?: string;
  labels?: string;
}

export const graphApi = {
  get: (slug: string, params?: GraphParams) =>
    api.get<GraphResponse>(`/projects/${slug}/graph`, { params }),
};
