import { api } from "./client";

export interface DeadLetterMessage {
  id: number;
  payload: Record<string, any>;
  original_status: string;
  retry_count: number;
  error: string | null;
  moved_at: string | null;
}

export interface DeadLetterListResponse {
  total: number;
  items: DeadLetterMessage[];
}

export interface QueueStats {
  queue: {
    pending: number;
    processing: number;
    total: number;
  };
  dead_letter: number;
}

export const monitoringApi = {
  listDeadLetter: (params?: Record<string, any>) =>
    api.get<DeadLetterListResponse>("/monitoring/dead-letter", { params }).then((r) => r.data),

  retryDeadLetter: (msgId: number) =>
    api.post(`/monitoring/dead-letter/${msgId}/retry`).then((r) => r.data),

  deleteDeadLetter: (msgId: number) =>
    api.delete(`/monitoring/dead-letter/${msgId}`).then((r) => r.data),

  getQueueStats: () =>
    api.get<QueueStats>("/monitoring/queue-stats").then((r) => r.data),
};
