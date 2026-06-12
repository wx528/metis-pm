import { api } from "./client";

export interface Notification {
  id: number;
  recipient: string;
  type: string;
  title: string;
  body: string | null;
  entity_type: string | null;
  entity_id: number | null;
  read: boolean;
  created_by: string | null;
  project_id: number | null;
  created_at: string;
  updated_at: string | null;
}

export interface NotificationListResponse {
  total: number;
  items: Notification[];
}

export interface NotificationListParams {
  skip?: number;
  limit?: number;
  unread_only?: boolean;
  project_id?: number;
  notification_type?: string;
}

export const notificationsApi = {
  list: (params?: NotificationListParams) =>
    api.get<NotificationListResponse>("/notifications", { params }).then((r) => r.data),
  unreadCount: () => api.get<{ count: number }>("/notifications/unread-count").then((r) => r.data),
  markRead: (id: number) => api.put<Notification>(`/notifications/${id}/read`).then((r) => r.data),
  markAllRead: () => api.put("/notifications/read-all"),
  batchMarkRead: (ids: number[]) =>
    api.put("/notifications/batch-read", ids),
  batchDelete: (ids: number[]) =>
    api.delete("/notifications/batch", { data: ids }),
};
