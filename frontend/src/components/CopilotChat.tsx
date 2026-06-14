import { useState, useRef, useEffect } from "react";
import { Input, Button, List, Typography, Tag, Avatar, Space, Empty } from "antd";
import { SendOutlined, RobotOutlined, UserOutlined, CloseOutlined } from "@ant-design/icons";

const { Text } = Typography;

interface ChatMessage {
  id: string;
  role: "user" | "copilot";
  content: string;
  timestamp: Date;
}

interface CopilotChatProps {
  open: boolean;
  onClose: () => void;
}

export default function CopilotChat({ open, onClose }: CopilotChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      role: "copilot",
      content: "你好！我是 PM Copilot。目前处于待连接状态，pm-copilot-engine 就绪后即可开始智能对话。",
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState("");
  const [connected, setConnected] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [messages]);

  useEffect(() => {
    fetch("/api/system/config")
      .then((r) => r.ok ? r.json() : null)
      .then((data) => { if (data?.ai_enabled) setConnected(true); })
      .catch(() => {});
  }, []);

  const handleSend = async () => {
    if (!input.trim()) return;
    const userMsg: ChatMessage = { id: Date.now().toString(), role: "user", content: input.trim(), timestamp: new Date() };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");

    if (!connected) {
      setMessages((prev) => [...prev, {
        id: (Date.now() + 1).toString(), role: "copilot",
        content: "Copilot 引擎未启用。请设置 PM_COPILOT_ENABLED=true 并启动 pm-copilot-engine。",
        timestamp: new Date(),
      }]);
      return;
    }

    setMessages((prev) => [...prev, {
      id: (Date.now() + 1).toString(), role: "copilot",
      content: "思考中...", timestamp: new Date(),
    }]);
  };

  if (!open) return null;

  return (
    <div style={{
      position: "fixed", bottom: 16, right: 16, width: 380, height: 520,
      background: "var(--ant-color-bg-container)", border: "1px solid var(--ant-color-border)",
      borderRadius: 12, boxShadow: "0 8px 24px rgba(0,0,0,0.15)", display: "flex", flexDirection: "column",
      zIndex: 1000,
    }}>
      <div style={{
        padding: "12px 16px", borderBottom: "1px solid var(--ant-color-border)",
        display: "flex", alignItems: "center", justifyContent: "space-between",
      }}>
        <Space>
          <RobotOutlined style={{ fontSize: 18 }} />
          <Text strong>PM Copilot</Text>
          <Tag color={connected ? "green" : "default"} style={{ fontSize: 10, margin: 0 }}>
            {connected ? "已连接" : "待连接"}
          </Tag>
        </Space>
        <Button type="text" size="small" icon={<CloseOutlined />} onClick={onClose} />
      </div>

      <div ref={listRef} style={{ flex: 1, overflow: "auto", padding: 16 }}>
        {messages.length === 0 ? (
          <Empty description="开始对话" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        ) : (
          <List
            dataSource={messages}
            renderItem={(msg) => (
              <div style={{ display: "flex", marginBottom: 12, flexDirection: msg.role === "user" ? "row-reverse" : "row" }}>
                <Avatar size={28} icon={msg.role === "user" ? <UserOutlined /> : <RobotOutlined />}
                  style={{ background: msg.role === "user" ? "#1677ff" : "#722ed1", flexShrink: 0 }} />
                <div style={{
                  margin: "0 8px", padding: "8px 12px", borderRadius: 8, maxWidth: 260,
                  background: msg.role === "user" ? "#e6f4ff" : "var(--ant-color-fill-secondary)",
                  fontSize: 13, lineHeight: 1.5,
                }}>
                  {msg.content}
                </div>
              </div>
            )}
          />
        )}
      </div>

      <div style={{ padding: 12, borderTop: "1px solid var(--ant-color-border)" }}>
        <Input.Search
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onSearch={handleSend}
          placeholder={connected ? "问 Copilot 任何问题..." : "Copilot 引擎未启用"}
          enterButton={<SendOutlined />}
          disabled={!connected}
        />
      </div>
    </div>
  );
}
