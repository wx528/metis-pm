import { useState } from "react";
import { Layout as AntLayout, Menu, Button, Tag, Dropdown, Badge, Drawer, List, Space, Typography } from "antd";
import { Outlet, useNavigate, useLocation } from "react-router-dom";
import {
  DashboardOutlined,
  BugOutlined,
  FlagOutlined,
  ProjectOutlined,
  CloudServerOutlined,
  LogoutOutlined,
  UserOutlined,
  BellOutlined,
  CheckOutlined,
  SwapOutlined,
} from "@ant-design/icons";
import { useAuth } from "../hooks/useAuth";
import { useProject } from "../hooks/useProject";
import { useNotifications } from "../hooks/useNotifications";
import type { MenuProps } from "antd";

const { Header, Sider, Content, Footer } = AntLayout;

export default function Layout() {
  const navigate = useNavigate();
  const location = useLocation();
  const { logout, sub, role } = useAuth();
  const { currentProject, projects, setCurrentProject } = useProject();
  const { unreadCount, notifications, refreshNotifications, markRead, markAllRead } = useNotifications();
  const [notifOpen, setNotifOpen] = useState(false);

  const basePath = currentProject ? `/projects/${currentProject.slug}` : "";

  const menuItems = [
    { key: `${basePath}/dashboard` || "/", icon: <DashboardOutlined />, label: "仪表盘" },
    { key: `${basePath}/issues`, icon: <BugOutlined />, label: "Issues" },
    { key: `${basePath}/milestones`, icon: <FlagOutlined />, label: "Milestones" },
    { key: `${basePath}/plans`, icon: <ProjectOutlined />, label: "Plans" },
    { key: `${basePath}/servers`, icon: <CloudServerOutlined />, label: "Servers" },
  ];

  // 确定当前选中的菜单项
  const selectedKey = menuItems.find((item) => location.pathname.startsWith(item.key))?.key || basePath || "/";

  const projectMenuItems: MenuProps["items"] = projects.map((p) => ({
    key: p.slug,
    label: (
      <span>
        {p.name}{" "}
        <Tag color={p.status === "active" ? "green" : "default"} style={{ fontSize: 10 }}>
          {p.status === "active" ? `${p.issue_count || 0} issues` : p.status}
        </Tag>
      </span>
    ),
  }));

  const handleProjectSwitch: MenuProps["onClick"] = ({ key }) => {
    const project = projects.find((p) => p.slug === key);
    if (project) {
      setCurrentProject(project);
      navigate(`/projects/${project.slug}/dashboard`);
    }
  };

  const notifTypeColor: Record<string, string> = {
    approval_needed: "orange",
    task_completed: "green",
    task_failed: "red",
    mention: "blue",
    workflow_paused: "purple",
    info: "default",
  };

  return (
    <AntLayout style={{ minHeight: "100vh" }}>
      <Sider theme="light" width={200}>
        {/* 项目切换器 */}
        <div style={{ padding: "12px 16px" }}>
          <Dropdown menu={{ items: projectMenuItems, onClick: handleProjectSwitch }} trigger={["click"]}>
            <Button
              icon={<SwapOutlined />}
              style={{ width: "100%", textAlign: "left", overflow: "hidden", textOverflow: "ellipsis" }}
            >
              {currentProject?.name || "选择项目"}
            </Button>
          </Dropdown>
        </div>
        <Menu
          mode="inline"
          selectedKeys={[selectedKey]}
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
          {/* 通知铃铛 */}
          <Badge count={unreadCount} size="small" offset={[-4, 4]}>
            <Button
              type="text"
              icon={<BellOutlined />}
              onClick={() => {
                setNotifOpen(true);
                refreshNotifications();
              }}
            />
          </Badge>
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

      {/* 通知抽屉 */}
      <Drawer
        title={
          <Space>
            <span>通知</span>
            {unreadCount > 0 && (
              <Button size="small" type="link" icon={<CheckOutlined />} onClick={markAllRead}>
                全部已读
              </Button>
            )}
          </Space>
        }
        open={notifOpen}
        onClose={() => setNotifOpen(false)}
        width={400}
      >
        <List
          dataSource={notifications}
          locale={{ emptyText: "暂无通知" }}
          renderItem={(item) => (
            <List.Item
              style={{
                background: item.read ? "transparent" : "#f6ffed",
                padding: "8px 12px",
                borderRadius: 6,
                cursor: item.entity_type ? "pointer" : "default",
              }}
              onClick={() => {
                if (!item.read) markRead(item.id);
                // 点击跳转到关联实体
                if (item.entity_type === "issue" && item.entity_id) {
                  navigate(`${basePath}/issues/${item.entity_id}`);
                  setNotifOpen(false);
                } else if (item.entity_type === "plan" && item.entity_id) {
                  navigate(`${basePath}/plans/${item.entity_id}`);
                  setNotifOpen(false);
                }
              }}
            >
              <List.Item.Meta
                title={
                  <Space>
                    <Tag color={notifTypeColor[item.type] || "default"} style={{ fontSize: 10 }}>
                      {item.type}
                    </Tag>
                    <span style={{ fontWeight: item.read ? "normal" : "bold" }}>{item.title}</span>
                  </Space>
                }
                description={
                  <Space direction="vertical" size={2}>
                    {item.body && <Typography.Text type="secondary" style={{ fontSize: 12 }}>{item.body}</Typography.Text>}
                    <Typography.Text type="secondary" style={{ fontSize: 11 }}>
                      {item.created_by && `by ${item.created_by} • `}
                      {new Date(item.created_at).toLocaleString()}
                    </Typography.Text>
                  </Space>
                }
              />
            </List.Item>
          )}
        />
      </Drawer>
    </AntLayout>
  );
}
