import { Spin } from "antd";

interface LoadingStateProps {
  message?: string;
}

export default function LoadingState({ message }: LoadingStateProps) {
  return (
    <div style={{ textAlign: "center", padding: "100px 0" }}>
      <Spin size="large" />
      {message && (
        <p style={{ marginTop: 16, color: "#888" }}>{message}</p>
      )}
    </div>
  );
}
