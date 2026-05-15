import { Layout as AntLayout, Menu, Button } from "antd";
import { Outlet, useNavigate, useLocation } from "react-router-dom";
import {
  DashboardOutlined,
  BugOutlined,
  FlagOutlined,
  ProjectOutlined,
  LogoutOutlined,
} from "@ant-design/icons";

const { Header, Sider, Content } = AntLayout;

const menuItems = [
  { key: "/", icon: <DashboardOutlined />, label: "仪表盘" },
  { key: "/issues", icon: <BugOutlined />, label: "Issues" },
  { key: "/milestones", icon: <FlagOutlined />, label: "Milestones" },
  { key: "/plans", icon: <ProjectOutlined />, label: "Plans" },
];

export default function Layout() {
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    localStorage.removeItem("token");
    window.location.href = "/login";
  };

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
            padding: "0 24px",
          }}
        >
          <Button icon={<LogoutOutlined />} onClick={handleLogout}>
            退出
          </Button>
        </Header>
        <Content style={{ margin: 24, padding: 24, background: "#fff", borderRadius: 8 }}>
          <Outlet />
        </Content>
      </AntLayout>
    </AntLayout>
  );
}
