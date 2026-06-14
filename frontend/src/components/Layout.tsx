import { useState, useEffect } from "react";
import { Layout as AntLayout, Menu, Button, Tag, Dropdown, Badge, Drawer, List, Space, Typography, Modal, Form, Input, Progress } from "antd";
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
  AppstoreOutlined,
  FolderOutlined,
  ThunderboltOutlined,
  SettingOutlined,
  DeleteOutlined,
  EditOutlined,
  PlusOutlined,
  RightOutlined,
  DownOutlined,
  FolderOpenOutlined,
  MessageOutlined,
  WarningOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  SunOutlined,
  MoonOutlined,
  ApartmentOutlined,
} from "@ant-design/icons";
import { useAuth } from "../hooks/useAuth";
import { useProject } from "../hooks/useProject";
import { useNotifications } from "../hooks/useNotifications";
import { useTheme } from "../hooks/useTheme";
import CopilotChat from "./CopilotChat";
import type { MenuProps } from "antd";

const { Header, Sider, Content, Footer } = AntLayout;
const { Text } = Typography;

interface GlobalResource {
  id: string;
  category: string;
  name: string;
  current: number;
  total: number;
  unit: string;
}

export default function Layout() {
  const navigate = useNavigate();
  const location = useLocation();
  const { logout, sub, role } = useAuth();
  const { currentProject, projects, setCurrentProject } = useProject();
  const { unreadCount, notifications, refreshNotifications, markRead, markAllRead } = useNotifications();
  const { theme, toggleTheme } = useTheme();
  const [notifOpen, setNotifOpen] = useState(false);
  const [copilotOpen, setCopilotOpen] = useState(false);

  // 响应式：移动端侧边栏折叠
  const [collapsed, setCollapsed] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const checkMobile = () => {
      const mobile = window.innerWidth < 768;
      setIsMobile(mobile);
      if (mobile) setCollapsed(true);
    };
    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  // 全局资源管理
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [resourceModalOpen, setResourceModalOpen] = useState(false);
  const [editingResource, setEditingResource] = useState<GlobalResource | null>(null);
  const [resources, setResources] = useState<GlobalResource[]>([]);
  const [expandedCategories, setExpandedCategories] = useState<Record<string, boolean>>({});
  const [resourceForm] = Form.useForm();

  useEffect(() => {
    try {
      const saved = localStorage.getItem("pm_global_resources");
      if (saved) {
        const parsed: GlobalResource[] = JSON.parse(saved);
        const migrated = parsed.map((r) => ({ ...r, category: r.category || "其他" }));
        setResources(migrated);
        localStorage.setItem("pm_global_resources", JSON.stringify(migrated));
        const cats: Record<string, boolean> = {};
        migrated.forEach((r) => { cats[r.category] = true; });
        setExpandedCategories(cats);
      } else {
        const defaults: GlobalResource[] = [
          { id: "code-plan", category: "Code Plans", name: "Code Plan", current: 0, total: 1000, unit: "次/月" },
          { id: "token-plan", category: "Token Plans", name: "Token Plan", current: 0, total: 1_000_000, unit: "tokens/月" },
        ];
        setResources(defaults);
        localStorage.setItem("pm_global_resources", JSON.stringify(defaults));
        setExpandedCategories({ "Code Plans": true, "Token Plans": true });
      }
    } catch {
      setResources([]);
    }
  }, []);

  const saveResources = (list: GlobalResource[]) => {
    setResources(list);
    localStorage.setItem("pm_global_resources", JSON.stringify(list));
  };

  const handleAddResource = (values: any) => {
    const newResource: GlobalResource = {
      id: values.id || Date.now().toString(),
      category: values.category || "其他",
      name: values.name,
      current: Number(values.current) || 0,
      total: Number(values.total) || 0,
      unit: values.unit || "",
    };
    if (editingResource) {
      saveResources(resources.map((r) => (r.id === editingResource.id ? newResource : r)));
    } else {
      const newList = [...resources, newResource];
      saveResources(newList);
      setExpandedCategories((prev) => ({ ...prev, [newResource.category]: true }));
    }
    setResourceModalOpen(false);
    setEditingResource(null);
    resourceForm.resetFields();
  };

  const handleDeleteResource = (id: string) => {
    saveResources(resources.filter((r) => r.id !== id));
  };

  const openEditResource = (r: GlobalResource) => {
    setEditingResource(r);
    resourceForm.setFieldsValue({
      id: r.id,
      category: r.category,
      name: r.name,
      current: r.current,
      total: r.total,
      unit: r.unit,
    });
    setResourceModalOpen(true);
  };

  const toggleCategory = (cat: string) => {
    setExpandedCategories((prev) => ({ ...prev, [cat]: !prev[cat] }));
  };

  // 按类别分组 + 汇总
  const groupedResources = resources.reduce<Record<string, GlobalResource[]>>((acc, r) => {
    const cat = r.category || "其他";
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(r);
    return acc;
  }, {});
  const categories = Object.keys(groupedResources).sort();

  const getCategorySummary = (cat: string) => {
    const items = groupedResources[cat];
    if (!items || items.length === 0) return { pct: 0, label: "" };
    const sumCurrent = items.reduce((s, r) => s + r.current, 0);
    const sumTotal = items.reduce((s, r) => s + r.total, 0);
    const pct = sumTotal > 0 ? Math.round((sumCurrent / sumTotal) * 100) : 0;
    return { pct, label: `${pct}%` };
  };

  const basePath = currentProject ? `/projects/${currentProject.slug}` : "";

  const menuItems = [
    { key: `${basePath}/dashboard` || "/", icon: <DashboardOutlined />, label: "仪表盘" },
    { key: `${basePath}/board`, icon: <AppstoreOutlined />, label: "看板" },
    { key: `${basePath}/graph`, icon: <ApartmentOutlined />, label: "Graph" },
    { key: `${basePath}/issues`, icon: <BugOutlined />, label: "Issues" },
    { key: `${basePath}/milestones`, icon: <FlagOutlined />, label: "Milestones" },
    { key: `${basePath}/plans`, icon: <ProjectOutlined />, label: "Plans" },
    { key: `${basePath}/servers`, icon: <CloudServerOutlined />, label: "Servers" },
    { key: `${basePath}/workflows`, icon: <ThunderboltOutlined />, label: "工作流" },
    { key: `/projects`, icon: <FolderOutlined />, label: "项目管理" },
    { key: `/project-registrations`, icon: <FolderOpenOutlined />, label: "项目登记" },
    { key: `/git-integration`, icon: <SettingOutlined />, label: "Git 集成" },
    { key: `/notifications`, icon: <BellOutlined />, label: "通知中心" },
    { key: `/feedbacks`, icon: <MessageOutlined />, label: "意见箱" },
    { key: `/risk-alerts`, icon: <WarningOutlined />, label: "风险告警" },
    { key: `/dead-letter`, icon: <WarningOutlined />, label: "死信队列" },
  ];

  const selectedKey =
    menuItems.find((item) => {
      if (item.key === "/projects") return location.pathname === "/projects";
      if (item.key === "/project-registrations") return location.pathname === "/project-registrations";
      if (item.key === "/git-integration") return location.pathname === "/git-integration";
      if (item.key === "/notifications") return location.pathname === "/notifications";
      if (item.key === "/feedbacks") return location.pathname === "/feedbacks";
      if (item.key === "/risk-alerts") return location.pathname === "/risk-alerts";
      if (item.key === "/dead-letter") return location.pathname === "/dead-letter";
      return location.pathname.startsWith(item.key);
    })?.key || basePath || "/";

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
    task_created: "blue",
    task_completed: "green",
    task_failed: "red",
    mention: "blue",
    workflow_paused: "purple",
    info: "default",
  };

  return (
    <AntLayout style={{ minHeight: "100vh" }}>
      <Sider
        theme={theme === "dark" ? "dark" : "light"}
        width={220}
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        trigger={null}
        breakpoint="md"
        style={{
          display: "flex",
          flexDirection: "column",
          height: "100vh",
          overflow: "hidden",
          position: isMobile ? "fixed" : "relative",
          zIndex: isMobile ? 100 : "auto",
          left: 0,
          top: 0,
        }}
      >
        {/* 移动端遮罩 */}
        {isMobile && !collapsed && (
          <div
            onClick={() => setCollapsed(true)}
            style={{
              position: "fixed",
              top: 0,
              left: 220,
              right: 0,
              bottom: 0,
              background: "rgba(0,0,0,0.3)",
              zIndex: -1,
            }}
          />
        )}
        {/* 项目切换器 */}
        <div style={{ padding: collapsed ? "12px 8px" : "12px 16px" }}>
          <Dropdown menu={{ items: projectMenuItems, onClick: handleProjectSwitch }} trigger={["click"]}>
            <Button
              icon={<SwapOutlined />}
              style={{ width: "100%", textAlign: "left", overflow: "hidden", textOverflow: "ellipsis" }}
            >
              {!collapsed && (currentProject?.name || "选择项目")}
            </Button>
          </Dropdown>
        </div>

        {/* 项目菜单 */}
        <div style={{ flex: "1 1 auto", overflowY: "auto" }}>
          <Menu
            mode="inline"
            selectedKeys={[selectedKey]}
            items={menuItems}
            onClick={({ key }) => {
              navigate(key);
              if (isMobile) setCollapsed(true);
            }}
            style={{ border: "none" }}
          />
        </div>

        {/* 底部：全局资源概览 - 固定不滚动 */}
        {!collapsed && (
          <div style={{ flex: "0 0 auto", borderTop: `1px solid ${theme === "dark" ? "#303030" : "#f0f0f0"}` }}>
            {/* 标题行 */}
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                padding: "10px 16px 6px",
              }}
            >
              <Text type="secondary" style={{ fontSize: 12, fontWeight: 600, letterSpacing: 1, textTransform: "uppercase" }}>
                全局资源
              </Text>
              <Button type="link" size="small" style={{ fontSize: 12, padding: 0, height: "auto" }} onClick={() => setDrawerOpen(true)}>
                管理
              </Button>
            </div>

            {/* 每个类别一行汇总进度 */}
            <div style={{ padding: "0 16px 12px" }}>
              {categories.length === 0 && (
                <Text type="secondary" style={{ fontSize: 11 }}>暂无资源</Text>
              )}
              {categories.map((cat) => {
                const { pct } = getCategorySummary(cat);
                return (
                  <div
                    key={cat}
                    style={{ marginBottom: 6, cursor: "pointer" }}
                    onClick={() => setDrawerOpen(true)}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 2 }}>
                      <Text style={{ fontSize: 12 }}>{cat}</Text>
                      <Text type="secondary" style={{ fontSize: 11 }}>{pct}%</Text>
                    </div>
                    <Progress
                      percent={pct}
                      showInfo={false}
                      size="small"
                      strokeColor={pct >= 90 ? "#ff4d4f" : pct >= 70 ? "#faad14" : "#1890ff"}
                      trailColor={theme === "dark" ? "#303030" : "#f0f0f0"}
                    />
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </Sider>

      <AntLayout style={{ marginLeft: isMobile && collapsed ? 0 : undefined }}>
        <Header
          style={{
            background: theme === "dark" ? "#141414" : "#fff",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: 12,
            padding: isMobile ? "0 12px" : "0 24px",
            borderBottom: `1px solid ${theme === "dark" ? "#303030" : "#f0f0f0"}`,
          }}
        >
          {/* 左侧：折叠按钮 */}
          <Button
            type="text"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setCollapsed(!collapsed)}
            style={{ fontSize: 16 }}
          />

          {/* 右侧操作区 */}
          <Space size={isMobile ? 4 : 12}>
            {/* 主题切换 */}
            <Button
              type="text"
              icon={theme === "dark" ? <SunOutlined /> : <MoonOutlined />}
              onClick={toggleTheme}
              title={theme === "dark" ? "切换到亮色模式" : "切换到暗色模式"}
            />

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

            {sub && !isMobile && (
              <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <UserOutlined />
                <span>{sub}</span>
                <Tag color={role === "admin" ? "blue" : "green"}>{role === "admin" ? "管理员" : "Agent"}</Tag>
              </span>
            )}
            <Button icon={<LogoutOutlined />} onClick={logout} size={isMobile ? "small" : "middle"}>
              {!isMobile && "退出"}
            </Button>
          </Space>
        </Header>
        <Content
          style={{
            margin: isMobile ? 8 : 24,
            padding: isMobile ? 12 : 24,
            background: theme === "dark" ? "#1f1f1f" : "#fff",
            borderRadius: 8,
            flex: 1,
            overflow: "auto",
          }}
        >
          <Outlet />
        </Content>
        <Footer style={{ textAlign: "center", padding: "12px 24px" }}>
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

      {/* 全局资源管理 Drawer */}
      <Drawer
        title={
          <Space>
            <SettingOutlined />
            <span>全局资源</span>
          </Space>
        }
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        width={480}
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            size="small"
            onClick={() => {
              setEditingResource(null);
              resourceForm.resetFields();
              setResourceModalOpen(true);
            }}
          >
            添加资源
          </Button>
        }
      >
        {resources.length === 0 && (
          <div style={{ textAlign: "center", padding: 60, color: "#999" }}>
            <SettingOutlined style={{ fontSize: 36, marginBottom: 12, display: "block" }} />
            暂无资源，点击右上角添加
          </div>
        )}
        {categories.map((cat) => {
          const isExpanded = expandedCategories[cat];
          const catResources = groupedResources[cat];
          const { pct } = getCategorySummary(cat);
          return (
            <div key={cat} style={{ marginBottom: 12 }}>
              {/* 类别头 - 可折叠 */}
              <div
                onClick={() => toggleCategory(cat)}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "10px 14px",
                  borderRadius: 8,
                  cursor: "pointer",
                  background: "#fafafa",
                  border: "1px solid #f0f0f0",
                  userSelect: "none",
                }}
              >
                <Space size={8}>
                  {isExpanded ? <DownOutlined style={{ fontSize: 11 }} /> : <RightOutlined style={{ fontSize: 11 }} />}
                  <Text strong>{cat}</Text>
                  <Tag style={{ fontSize: 11 }}>{catResources.length}</Tag>
                </Space>
                <Space size={8} align="center">
                  <Progress type="circle" percent={pct} size={28} strokeColor={pct >= 90 ? "#ff4d4f" : pct >= 70 ? "#faad14" : "#1890ff"} />
                </Space>
              </div>

              {/* 展开的资源列表 */}
              {isExpanded && (
                <div style={{ padding: "8px 0 0 0" }}>
                  {catResources.map((r) => {
                    const rPct = r.total > 0 ? Math.round((r.current / r.total) * 100) : 0;
                    return (
                      <div
                        key={r.id}
                        style={{
                          padding: "12px 14px",
                          borderRadius: 6,
                          marginBottom: 6,
                          background: "#fff",
                          border: "1px solid #f0f0f0",
                        }}
                      >
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                          <Text strong>{r.name}</Text>
                          <Space size={4}>
                            <Button type="text" icon={<EditOutlined />} size="small" onClick={() => openEditResource(r)} />
                            <Button type="text" danger icon={<DeleteOutlined />} size="small" onClick={() => handleDeleteResource(r.id)} />
                          </Space>
                        </div>
                        <Progress
                          percent={rPct}
                          size="small"
                          status={rPct >= 100 ? "exception" : "active"}
                        />
                        <div style={{ display: "flex", justifyContent: "space-between", marginTop: 4 }}>
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            已用 {r.current.toLocaleString()} / {r.total.toLocaleString()} {r.unit}
                          </Text>
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            剩余 {Math.max(0, r.total - r.current).toLocaleString()} {r.unit}
                          </Text>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </Drawer>

      {/* 资源添加/编辑弹窗 */}
      <Modal
        title={editingResource ? "编辑资源" : "添加资源"}
        open={resourceModalOpen}
        onCancel={() => {
          setResourceModalOpen(false);
          setEditingResource(null);
        }}
        onOk={() => resourceForm.submit()}
      >
        <Form form={resourceForm} onFinish={handleAddResource} layout="vertical">
          <Form.Item name="category" label="所属类别" rules={[{ required: true, message: "请输入类别" }]}>
            <Input placeholder="如 Token Plans、Code Plans，或输入新类别" list="resource-categories" />
          </Form.Item>
          <datalist id="resource-categories">
            {categories.map((cat) => (
              <option key={cat} value={cat} />
            ))}
          </datalist>
          <Form.Item name="name" label="资源名称" rules={[{ required: true, message: "请输入资源名称" }]}>
            <Input placeholder="如 Code Plan" />
          </Form.Item>
          <Form.Item name="current" label="当前用量">
            <Input type="number" placeholder="0" />
          </Form.Item>
          <Form.Item name="total" label="总量上限">
            <Input type="number" placeholder="1000" />
          </Form.Item>
          <Form.Item name="unit" label="单位">
            <Input placeholder="如 次/月, tokens" />
          </Form.Item>
          {editingResource && (
            <Form.Item name="id" hidden>
              <Input />
            </Form.Item>
          )}
        </Form>
      </Modal>

      <Button
        type="primary"
        shape="circle"
        icon={<ApartmentOutlined />}
        onClick={() => setCopilotOpen(true)}
        style={{
          position: "fixed", bottom: 24, right: 24, width: 48, height: 48,
          background: "#722ed1", boxShadow: "0 4px 12px rgba(114,46,209,0.4)", zIndex: 999,
        }}
        title="PM Copilot"
      />
      <CopilotChat open={copilotOpen} onClose={() => setCopilotOpen(false)} />
    </AntLayout>
  );
}
