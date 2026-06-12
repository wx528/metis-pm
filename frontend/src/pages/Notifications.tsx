import { useState, useEffect } from "react";
import {
  Card,
  List,
  Badge,
  Button,
  Space,
  Select,
  Switch,
  Typography,
  message,
  Popconfirm,
  Empty,
  Tag,
} from "antd";
import {
  BellOutlined,
  CheckOutlined,
  FilterOutlined,
  ReloadOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { notificationsApi, type Notification } from "../api/notifications";

const { Text, Paragraph } = Typography;
const { Option } = Select;

// 通知类型配置
const notificationTypeConfig: Record<string, { label: string; color: string }> = {
  issue_created: { label: "Issue 创建", color: "blue" },
  issue_updated: { label: "Issue 更新", color: "blue" },
  issue_closed: { label: "Issue 关闭", color: "green" },
  plan_created: { label: "Plan 创建", color: "purple" },
  plan_approved: { label: "Plan 通过", color: "green" },
  plan_rejected: { label: "Plan 驳回", color: "red" },
  plan_completed: { label: "Plan 完成", color: "cyan" },
  workflow_completed: { label: "工作流完成", color: "green" },
  workflow_failed: { label: "工作流失败", color: "red" },
  comment_added: { label: "新评论", color: "orange" },
  approval_needed: { label: "需要审批", color: "gold" },
  system: { label: "系统通知", color: "default" },
};

// 实体类型跳转配置
const entityRouteMap: Record<string, (id: number) => string> = {
  issue: (id) => `/issues/${id}`,
  plan: (id) => `/plans/${id}`,
  workflow: (id) => `/workflows/${id}`,
};

export default function Notifications() {
  const navigate = useNavigate();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [typeFilter, setTypeFilter] = useState<string | undefined>();
  const [selectedIds, setSelectedIds] = useState<number[]>([]);

  useEffect(() => {
    loadNotifications();
  }, [page, pageSize, unreadOnly, typeFilter]);

  const loadNotifications = async () => {
    setLoading(true);
    try {
      const res = await notificationsApi.list({
        skip: (page - 1) * pageSize,
        limit: pageSize,
        unread_only: unreadOnly,
        notification_type: typeFilter,
      });
      setNotifications(res.items);
      setTotal(res.total);
    } catch (err) {
      message.error("加载通知失败");
    } finally {
      setLoading(false);
    }
  };

  const handleMarkRead = async (id: number) => {
    try {
      await notificationsApi.markRead(id);
      message.success("已标记为已读");
      loadNotifications();
    } catch (err) {
      message.error("操作失败");
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await notificationsApi.markAllRead();
      message.success("全部标记为已读");
      loadNotifications();
    } catch (err) {
      message.error("操作失败");
    }
  };

  const handleBatchMarkRead = async () => {
    if (selectedIds.length === 0) {
      message.warning("请先选择通知");
      return;
    }
    try {
      await notificationsApi.batchMarkRead(selectedIds);
      message.success(`已标记 ${selectedIds.length} 条通知为已读`);
      setSelectedIds([]);
      loadNotifications();
    } catch (err) {
      message.error("操作失败");
    }
  };

  const handleBatchDelete = async () => {
    if (selectedIds.length === 0) {
      message.warning("请先选择通知");
      return;
    }
    try {
      await notificationsApi.batchDelete(selectedIds);
      message.success(`已删除 ${selectedIds.length} 条通知`);
      setSelectedIds([]);
      loadNotifications();
    } catch (err) {
      message.error("操作失败");
    }
  };

  const handleNotificationClick = (notification: Notification) => {
    // 标记为已读
    if (!notification.read) {
      notificationsApi.markRead(notification.id);
    }

    // 跳转到相关实体
    if (notification.entity_type && notification.entity_id) {
      const routeBuilder = entityRouteMap[notification.entity_type];
      if (routeBuilder) {
        navigate(routeBuilder(notification.entity_id));
      }
    }
  };

  const handleSelectChange = (id: number, checked: boolean) => {
    if (checked) {
      setSelectedIds([...selectedIds, id]);
    } else {
      setSelectedIds(selectedIds.filter((i) => i !== id));
    }
  };

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedIds(notifications.map((n) => n.id));
    } else {
      setSelectedIds([]);
    }
  };

  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return "刚刚";
    if (minutes < 60) return `${minutes} 分钟前`;
    if (hours < 24) return `${hours} 小时前`;
    if (days < 7) return `${days} 天前`;
    return date.toLocaleDateString("zh-CN");
  };

  return (
    <div style={{ padding: 24 }}>
      <Card
        title={
          <Space>
            <BellOutlined />
            <span>通知中心</span>
            {total > 0 && (
              <Badge count={total} style={{ backgroundColor: "#1890ff" }} />
            )}
          </Space>
        }
        extra={
          <Space>
            <Button
              icon={<ReloadOutlined />}
              onClick={loadNotifications}
              loading={loading}
            >
              刷新
            </Button>
            <Button icon={<CheckOutlined />} onClick={handleMarkAllRead}>
              全部已读
            </Button>
          </Space>
        }
      >
        {/* 筛选栏 */}
        <div style={{ marginBottom: 16, display: "flex", gap: 16, alignItems: "center" }}>
          <Space>
            <FilterOutlined />
            <span>筛选：</span>
          </Space>
          <Switch
            checked={unreadOnly}
            onChange={setUnreadOnly}
            checkedChildren="仅未读"
            unCheckedChildren="全部"
          />
          <Select
            placeholder="通知类型"
            allowClear
            style={{ width: 150 }}
            value={typeFilter}
            onChange={setTypeFilter}
          >
            {Object.entries(notificationTypeConfig).map(([key, config]) => (
              <Option key={key} value={key}>
                {config.label}
              </Option>
            ))}
          </Select>
        </div>

        {/* 批量操作栏 */}
        {selectedIds.length > 0 && (
          <div
            style={{
              marginBottom: 16,
              padding: "8px 16px",
              backgroundColor: "#f0f5ff",
              borderRadius: 4,
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <Text>已选择 {selectedIds.length} 项</Text>
            <Space>
              <Button size="small" onClick={handleBatchMarkRead}>
                标记已读
              </Button>
              <Popconfirm
                title={`确定删除 ${selectedIds.length} 条通知？`}
                onConfirm={handleBatchDelete}
              >
                <Button size="small" danger>
                  删除
                </Button>
              </Popconfirm>
              <Button size="small" onClick={() => setSelectedIds([])}>
                取消选择
              </Button>
            </Space>
          </div>
        )}

        {/* 全选 */}
        {notifications.length > 0 && (
          <div style={{ marginBottom: 8 }}>
            <Switch
              checked={selectedIds.length === notifications.length && notifications.length > 0}
              onChange={handleSelectAll}
              checkedChildren="全选"
              unCheckedChildren="全选"
              size="small"
            />
          </div>
        )}

        {/* 通知列表 */}
        <List
          loading={loading}
          itemLayout="vertical"
          dataSource={notifications}
          locale={{ emptyText: <Empty description="暂无通知" /> }}
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
            onChange: (p, ps) => {
              setPage(p);
              if (ps) setPageSize(ps);
            },
          }}
          renderItem={(item) => {
            const config = notificationTypeConfig[item.type] || {
              label: item.type,
              color: "default",
            };

            return (
              <List.Item
                style={{
                  padding: "12px 16px",
                  backgroundColor: item.read ? "#fff" : "#f6ffed",
                  borderRadius: 4,
                  marginBottom: 8,
                  cursor: "pointer",
                }}
                onClick={() => handleNotificationClick(item)}
              >
                <List.Item.Meta
                  avatar={
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <input
                        type="checkbox"
                        checked={selectedIds.includes(item.id)}
                        onChange={(e) => handleSelectChange(item.id, e.target.checked)}
                        onClick={(e) => e.stopPropagation()}
                      />
                      {!item.read && <Badge status="processing" />}
                    </div>
                  }
                  title={
                    <Space>
                      <Text strong={!item.read}>{item.title}</Text>
                      <Tag color={config.color}>{config.label}</Tag>
                      {item.entity_type && item.entity_id && (
                        <Tag>
                          {item.entity_type} #{item.entity_id}
                        </Tag>
                      )}
                    </Space>
                  }
                  description={
                    <Space>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {formatTime(item.created_at)}
                      </Text>
                      {item.created_by && (
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          by {item.created_by}
                        </Text>
                      )}
                    </Space>
                  }
                />
                {item.body && (
                  <Paragraph
                    ellipsis={{ rows: 2, expandable: true }}
                    style={{ marginBottom: 0, marginTop: 8 }}
                  >
                    {item.body}
                  </Paragraph>
                )}
                {!item.read && (
                  <div style={{ marginTop: 8 }}>
                    <Button
                      size="small"
                      icon={<CheckOutlined />}
                      onClick={(e) => {
                        e.stopPropagation();
                        handleMarkRead(item.id);
                      }}
                    >
                      标记已读
                    </Button>
                  </div>
                )}
              </List.Item>
            );
          }}
        />
      </Card>
    </div>
  );
}
