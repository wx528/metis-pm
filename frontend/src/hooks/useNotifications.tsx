import { createContext, useContext, useState, useEffect, useCallback, useRef, type ReactNode } from "react";
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
  const sseConnected = useRef(false);
  const pollingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

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

  // 启动/停止轮询（SSE 连接时停止，断开时恢复）
  const startPolling = useCallback(() => {
    if (pollingIntervalRef.current) return;
    refreshUnreadCount();
    // 轮询降级：SSE 断开时使用较长间隔（60秒），避免频繁请求
    pollingIntervalRef.current = setInterval(refreshUnreadCount, 60000);
  }, [refreshUnreadCount]);

  const stopPolling = useCallback(() => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
  }, []);

  // 初始加载：先启动轮询，SSE 连接成功后自动停止
  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) return;
    startPolling();
    return () => stopPolling();
  }, [startPolling, stopPolling]);

  // SSE 实时推送
  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) return;

    const API_BASE = import.meta.env.VITE_API_URL || "/api/v1";
    const url = `${API_BASE}/notifications/stream`;

    let abortController: AbortController | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let reconnectDelay = 1000;
    const MAX_RECONNECT_DELAY = 30000;

    const connectSSE = () => {
      abortController = new AbortController();
      fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
        signal: abortController.signal,
      })
        .then((response) => {
          if (!response.ok || !response.body) {
            if (response.status === 401) return;
            scheduleReconnect();
            return;
          }
          // SSE 连接成功，停止轮询
          sseConnected.current = true;
          stopPolling();
          reconnectDelay = 1000;

          // 心跳检测：45 秒无数据则重连
          let lastDataTime = Date.now();
          const heartbeatCheck = setInterval(() => {
            if (Date.now() - lastDataTime > 45000) {
              clearInterval(heartbeatCheck);
              sseConnected.current = false;
              startPolling();
              abortController?.abort();
              scheduleReconnect();
            }
          }, 15000);

          const reader = response.body.getReader();
          const decoder = new TextDecoder();

          let currentEvent = "";

          const readChunk = () => {
            reader
              .read()
              .then(({ done, value }) => {
                if (done) {
                  clearInterval(heartbeatCheck);
                  sseConnected.current = false;
                  startPolling();
                  scheduleReconnect();
                  return;
                }
                lastDataTime = Date.now();
                const text = decoder.decode(value, { stream: true });
                // 解析 SSE 事件
                const lines = text.split("\n");
                for (const line of lines) {
                  if (line.startsWith("event: ")) {
                    currentEvent = line.slice(7).trim();
                  } else if (line.startsWith("data: ")) {
                    const data = line.slice(6);
                    if (currentEvent === "unread_count") {
                      // 服务端推送未读数
                      const count = parseInt(data, 10);
                      if (!isNaN(count)) {
                        setUnreadCount(count);
                      }
                    } else if (currentEvent === "notification") {
                      // 服务端推送新通知
                      try {
                        const notification = JSON.parse(data);
                        setNotifications((prev) => [notification, ...prev]);
                      } catch {
                        // ignore parse error
                      }
                    }
                    // heartbeat / connected 事件忽略
                    currentEvent = "";
                  }
                }
                readChunk();
              })
              .catch(() => {
                clearInterval(heartbeatCheck);
                sseConnected.current = false;
                startPolling();
                scheduleReconnect();
              });
          };
          readChunk();
        })
        .catch(() => {
          scheduleReconnect();
        });
    };

    const scheduleReconnect = () => {
      reconnectTimer = setTimeout(() => {
        connectSSE();
      }, reconnectDelay);
      reconnectDelay = Math.min(reconnectDelay * 2, MAX_RECONNECT_DELAY);
    };

    connectSSE();

    return () => {
      abortController?.abort();
      if (reconnectTimer) clearTimeout(reconnectTimer);
      sseConnected.current = false;
    };
  }, [startPolling, stopPolling]);

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
