import { api } from "./client";

export interface ActivityLog {
  id: number;
  entity_type: string;
  entity_id: number;
  action: string;
  old_value?: Record<string, any>;
  new_value?: Record<string, any>;
  actor: string;
  created_at: string;
}

export const activityLogsApi = {
  list: (entity_type: string, entity_id: number, limit?: number) =>
    api.get<ActivityLog[]>("/activity-logs", { params: { entity_type, entity_id, limit } }),
};
