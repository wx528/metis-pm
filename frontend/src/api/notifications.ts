import { api } from "./client";

export interface Notification { id: number; target_role: string; message: string; is_read: boolean; project_id?: number; created_at: string; }
export interface NotificationListResponse { total: number; items: Notification[]; }
export const notificationsApi = {
  list: (params?: Record<string, any>) => api.get<NotificationListResponse>("/notifications", { params }),
  unreadCount: () => api.get<{ count: number }>("/notifications/unread-count"),
  markRead: (id: number) => api.put<Notification>(`/notifications/${id}/read`),
  markAllRead: () => api.put("/notifications/read-all"),
};
