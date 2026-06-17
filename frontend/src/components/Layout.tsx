import { useState } from "react";
import { Outlet, useNavigate, useParams } from "react-router-dom";
import { Layout as AntLayout, Menu, Button, Drawer } from "antd";
import { DashboardOutlined, BugOutlined, ScheduleOutlined, MenuOutlined } from "@ant-design/icons";

const { Sider, Content, Header } = AntLayout;

export default function Layout() {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const navigate = useNavigate();
  const { projectSlug } = useParams<{ projectSlug: string }>();
  const slug = projectSlug || "default";

  const menuItems = [
    { key: "dashboard", icon: <DashboardOutlined />, label: "概览" },
    { key: "issues", icon: <BugOutlined />, label: "Issues" },
    { key: "plans", icon: <ScheduleOutlined />, label: "计划" },
  ];

  const handleMenuClick = (key: string) => {
    navigate(`/projects/${slug}/${key}`);
    setMobileOpen(false);
  };

  const sidebar = (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      <div style={{ padding: 16, fontWeight: 700, fontSize: 16, textAlign: "center", borderBottom: "1px solid #f0f0f0" }}>
        Metis PM
      </div>
      <Menu
        mode="inline"
        selectedKeys={[window.location.pathname.split("/").pop() || "dashboard"]}
        items={menuItems}
        onClick={({ key }) => handleMenuClick(key)}
        style={{ flex: 1, borderRight: 0 }}
      />
    </div>
  );

  return (
    <AntLayout style={{ minHeight: "100vh" }}>
      <Sider collapsible collapsed={collapsed} onCollapse={setCollapsed} breakpoint="lg">
        {sidebar}
      </Sider>
      <Drawer open={mobileOpen} onClose={() => setMobileOpen(false)} placement="left" width={250} styles={{ body: { padding: 0 } }}>
        {sidebar}
      </Drawer>
      <AntLayout>
        <Header style={{ background: "#fff", padding: "0 16px", display: "flex", alignItems: "center", gap: 12 }}>
          <Button type="text" icon={<MenuOutlined />} onClick={() => setMobileOpen(true)} className="mobile-menu-btn" />
          <span style={{ fontWeight: 600 }}>Metis PM</span>
        </Header>
        <Content style={{ margin: 16 }}>
          <Outlet />
        </Content>
      </AntLayout>
    </AntLayout>
  );
}
