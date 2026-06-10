import { Alert, Button } from "antd";
import { ReloadOutlined } from "@ant-design/icons";

interface ErrorStateProps {
  error: Error;
  onRetry?: () => void;
}

export default function ErrorState({ error, onRetry }: ErrorStateProps) {
  return (
    <div style={{ textAlign: "center", padding: "100px 0" }}>
      <Alert
        message="加载失败"
        description={error.message || "请稍后重试"}
        type="error"
        showIcon
        action={
          onRetry ? (
            <Button icon={<ReloadOutlined />} onClick={onRetry}>
              重试
            </Button>
          ) : undefined
        }
      />
    </div>
  );
}
