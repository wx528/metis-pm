import { useState } from "react";
import { Form, Input, Button, Card, message, Alert } from "antd";
import { authApi } from "../api/auth";

export default function Login() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const onFinish = async (values: { password: string }) => {
    setLoading(true);
    setError("");
    try {
      const res = await authApi.login(values.password);
      localStorage.setItem("token", res.data.token);
      message.success("登录成功");
      window.location.replace("/");
    } catch (err: any) {
      const msg = err.response?.data?.detail || "密码错误";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        height: "100vh",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        background: "#f0f2f5",
      }}
    >
      <Card title="Project Manager" style={{ width: 360 }}>
        {error && (
          <Alert
            message={error}
            type="error"
            showIcon
            style={{ marginBottom: 16 }}
            closable
            onClose={() => setError("")}
          />
        )}
        <Form onFinish={onFinish} layout="vertical">
          <Form.Item
            label="密码"
            name="password"
            rules={[{ required: true, message: "请输入密码" }]}
          >
            <Input.Password placeholder="请输入密码" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block>
              登录
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}
