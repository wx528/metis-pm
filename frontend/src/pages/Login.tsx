import { useState } from "react";
import { Form, Input, Button, Card, message, Alert, Layout } from "antd";
import { useNavigate } from "react-router-dom";
import { authApi } from "../api/auth";
import { useAuth } from "../hooks/useAuth";

const { Footer } = Layout;

export default function Login() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const { login } = useAuth();
  const navigate = useNavigate();

  const onFinish = async (values: { password: string }) => {
    setLoading(true);
    setError("");
    try {
      const res = await authApi.login(values.password);
      login(res.data.token, res.data.sub, res.data.role);
      message.success("登录成功");
      navigate("/", { replace: true });
    } catch (err: any) {
      const msg = err.response?.data?.detail || "密码错误";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Layout style={{ minHeight: "100vh", background: "#f0f2f5" }}>
      <div
        style={{
          flex: 1,
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
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
      <Footer style={{ textAlign: "center", background: "#f0f2f5", padding: "12px 24px" }}>
        Project Manager System v{__APP_VERSION__}
      </Footer>
    </Layout>
  );
}
