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

export const notificationsApi = {
  list: (params?: { skip?: number; limit?: number; unread_only?: boolean }) =>
    api.get<NotificationListResponse>("/notifications", { params }).then((r) => r.data),
  unreadCount: () => api.get<{ count: number }>("/notifications/unread-count").then((r) => r.data),
  markRead: (id: number) => api.put<Notification>(`/notifications/${id}/read`).then((r) => r.data),
  markAllRead: () => api.put("/notifications/read-all"),
};
