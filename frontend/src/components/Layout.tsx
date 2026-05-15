import { Layout as AntLayout, Menu, Button, Tag } from "antd";
import { Outlet, useNavigate, useLocation } from "react-router-dom";
import {
  DashboardOutlined,
  BugOutlined,
  FlagOutlined,
  ProjectOutlined,
  CloudServerOutlined,
  LogoutOutlined,
  UserOutlined,
} from "@ant-design/icons";
import { useAuth } from "../hooks/useAuth";

const { Header, Sider, Content, Footer } = AntLayout;

const menuItems = [
  { key: "/", icon: <DashboardOutlined />, label: "仪表盘" },
  { key: "/issues", icon: <BugOutlined />, label: "Issues" },
  { key: "/milestones", icon: <FlagOutlined />, label: "Milestones" },
  { key: "/plans", icon: <ProjectOutlined />, label: "Plans" },
  { key: "/servers", icon: <CloudServerOutlined />, label: "Servers" },
];

export default function Layout() {
  const navigate = useNavigate();
  const location = useLocation();
  const { logout, sub, role } = useAuth();

  return (
    <AntLayout style={{ minHeight: "100vh" }}>
      <Sider theme="light" width={200}>
        <div style={{ padding: 16, fontSize: 18, fontWeight: "bold", textAlign: "center" }}>
          PM System
        </div>
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <AntLayout>
        <Header
          style={{
            background: "#fff",
            display: "flex",
            justifyContent: "flex-end",
            alignItems: "center",
            gap: 12,
            padding: "0 24px",
          }}
        >
          {sub && (
            <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <UserOutlined />
              <span>{sub}</span>
              <Tag color={role === "admin" ? "blue" : "green"}>{role === "admin" ? "管理员" : "Agent"}</Tag>
            </span>
          )}
          <Button icon={<LogoutOutlined />} onClick={logout}>
            退出
          </Button>
        </Header>
        <Content style={{ margin: 24, padding: 24, background: "#fff", borderRadius: 8, flex: 1 }}>
          <Outlet />
        </Content>
        <Footer style={{ textAlign: "center", background: "#f0f2f5", padding: "12px 24px" }}>
          Project Manager System v{__APP_VERSION__}
        </Footer>
      </AntLayout>
    </AntLayout>
  );
}
