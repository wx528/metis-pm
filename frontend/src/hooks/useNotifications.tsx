import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";
import { notificationsApi, type Notification } from "../api/notifications";

interface NotificationContextType {
  unreadCount: number;
  notifications: Notification[];
  refreshUnreadCount: () => Promise<void>;
  refreshNotifications: () => Promise<void>;
  markRead: (id: number) => Promise<void>;
  markAllRead: () => Promise<void>;
}

const NotificationContext = createContext<NotificationContextType>({
  unreadCount: 0,
  notifications: [],
  refreshUnreadCount: async () => {},
  refreshNotifications: async () => {},
  markRead: async () => {},
  markAllRead: async () => {},
});

export function NotificationProvider({ children }: { children: ReactNode }) {
  const [unreadCount, setUnreadCount] = useState(0);
  const [notifications, setNotifications] = useState<Notification[]>([]);

  const refreshUnreadCount = useCallback(async () => {
    try {
      const data = await notificationsApi.unreadCount();
      setUnreadCount(data.count);
    } catch {
      // ignore
    }
  }, []);

  const refreshNotifications = useCallback(async () => {
    try {
      const data = await notificationsApi.list({ limit: 50 });
      setNotifications(data.items);
    } catch {
      // ignore
    }
  }, []);

  const markRead = useCallback(async (id: number) => {
    try {
      await notificationsApi.markRead(id);
      setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, read: true } : n)));
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch {
      // ignore
    }
  }, []);

  const markAllRead = useCallback(async () => {
    try {
      await notificationsApi.markAllRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
      setUnreadCount(0);
    } catch {
      // ignore
    }
  }, []);

  // 初始加载 + 定时刷新
  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) return;

    refreshUnreadCount();
    const interval = setInterval(refreshUnreadCount, 30000); // 30 秒轮询
    return () => clearInterval(interval);
  }, [refreshUnreadCount]);

  // SSE 实时推送
  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) return;

    const API_BASE = import.meta.env.VITE_API_URL || "/api/v1";
    const url = `${API_BASE}/notifications/stream?token=${token}`;

    // EventSource 不支持自定义 header，用 fetch + ReadableStream 替代
    let abortController: AbortController | null = null;

    const connectSSE = () => {
      abortController = new AbortController();
      fetch(url.replace("?token=", ""), {
        headers: { Authorization: `Bearer ${token}` },
        signal: abortController.signal,
      })
        .then((response) => {
          if (!response.ok || !response.body) return;
          const reader = response.body.getReader();
          const decoder = new TextDecoder();

          const readChunk = () => {
            reader
              .read()
              .then(({ done, value }) => {
                if (done) return;
                const text = decoder.decode(value, { stream: true });
                // 解析 SSE 数据
                const lines = text.split("\n");
                for (const line of lines) {
                  if (line.startsWith("data: ")) {
                    try {
                      const notification = JSON.parse(line.slice(6));
                      setNotifications((prev) => [notification, ...prev]);
                      setUnreadCount((prev) => prev + 1);
                    } catch {
                      // heartbeat or non-JSON, ignore
                    }
                  }
                }
                readChunk();
              })
              .catch(() => {
                // connection lost, will reconnect
              });
          };
          readChunk();
        })
        .catch(() => {
          // SSE connection failed, fall back to polling
        });
    };

    connectSSE();

    return () => {
      abortController?.abort();
    };
  }, []);

  return (
    <NotificationContext.Provider
      value={{ unreadCount, notifications, refreshUnreadCount, refreshNotifications, markRead, markAllRead }}
    >
      {children}
    </NotificationContext.Provider>
  );
}

export function useNotifications() {
  return useContext(NotificationContext);
}
