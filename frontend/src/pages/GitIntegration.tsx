import { useState, useEffect } from "react";
import {
  Card,
  Table,
  Button,
  Modal,
  Form,
  Input,
  Select,
  Switch,
  Tag,
  Space,
  message,
  Popconfirm,
  Typography,
  Descriptions,
  Alert,
} from "antd";
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  CopyOutlined,
  ReloadOutlined,
  GithubOutlined,
  CheckCircleOutlined,
} from "@ant-design/icons";
import {
  gitIntegrationApi,
  type GitIntegration,
  type GitIntegrationCreate,
  type GitIntegrationUpdate,
} from "../api/gitIntegration";
import { useProject } from "../hooks/useProject";

const { Text } = Typography;
const { Option } = Select;

const platformLabels: Record<string, { label: string; icon: React.ReactNode; color: string }> = {
  github: { label: "GitHub", icon: <GithubOutlined />, color: "#24292e" },
  gitea: { label: "Gitea", icon: <GithubOutlined />, color: "#609926" },
  forgejo: { label: "Forgejo", icon: <GithubOutlined />, color: "#417198" },
};

const eventLabels: Record<string, string> = {
  push: "代码推送",
  pull_request: "Pull Request",
  issues: "Issues",
};

export default function GitIntegrationSettings() {
  const { currentProject } = useProject();
  const [integrations, setIntegrations] = useState<GitIntegration[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingIntegration, setEditingIntegration] = useState<GitIntegration | null>(null);
  const [form] = Form.useForm();
  const [secretModalVisible, setSecretModalVisible] = useState(false);
  const [generatedSecret, setGeneratedSecret] = useState("");

  useEffect(() => {
    if (currentProject) {
      loadIntegrations();
    }
  }, [currentProject]);

  const loadIntegrations = async () => {
    setLoading(true);
    try {
      const res = await gitIntegrationApi.list(currentProject?.id);
      setIntegrations(res.data);
    } catch (err) {
      message.error("加载集成配置失败");
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = () => {
    setEditingIntegration(null);
    form.resetFields();
    form.setFieldsValue({
      project_id: currentProject?.id,
      auto_close_issue: true,
      auto_link_pr: true,
      subscribed_events: ["push", "pull_request"],
    });
    setModalVisible(true);
  };

  const handleEdit = (integration: GitIntegration) => {
    setEditingIntegration(integration);
    form.setFieldsValue({
      ...integration,
      webhook_secret: undefined, // 不显示已有 secret
    });
    setModalVisible(true);
  };

  const handleDelete = async (id: number) => {
    try {
      await gitIntegrationApi.delete(id);
      message.success("删除成功");
      loadIntegrations();
    } catch (err) {
      message.error("删除失败");
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();

      if (editingIntegration) {
        const updateData: GitIntegrationUpdate = {
          repo_url: values.repo_url,
          auto_close_issue: values.auto_close_issue,
          auto_link_pr: values.auto_link_pr,
          subscribed_events: values.subscribed_events,
        };
        if (values.webhook_secret) {
          updateData.webhook_secret = values.webhook_secret;
        }
        await gitIntegrationApi.update(editingIntegration.id, updateData);
        message.success("更新成功");
      } else {
        const createData: GitIntegrationCreate = {
          project_id: currentProject!.id,
          repo_url: values.repo_url,
          platform: values.platform,
          webhook_secret: values.webhook_secret,
          auto_close_issue: values.auto_close_issue,
          auto_link_pr: values.auto_link_pr,
          subscribed_events: values.subscribed_events,
        };
        await gitIntegrationApi.create(createData);
        message.success("创建成功");
      }

      setModalVisible(false);
      loadIntegrations();
    } catch (err: any) {
      if (err.errorFields) return; // 表单验证错误
      message.error("操作失败");
    }
  };

  const handleRegenerateSecret = async (id: number) => {
    try {
      const res = await gitIntegrationApi.regenerateSecret(id);
      setGeneratedSecret(res.data.secret);
      setSecretModalVisible(true);
      loadIntegrations();
    } catch (err) {
      message.error("重新生成失败");
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    message.success("已复制到剪贴板");
  };

  const columns = [
    {
      title: "平台",
      dataIndex: "platform",
      key: "platform",
      render: (platform: string) => {
        const cfg = platformLabels[platform];
        return (
          <Tag color={cfg?.color} icon={cfg?.icon}>
            {cfg?.label || platform}
          </Tag>
        );
      },
    },
    {
      title: "仓库",
      dataIndex: "repo_url",
      key: "repo_url",
      ellipsis: true,
      render: (url: string) => (
        <a href={url} target="_blank" rel="noopener noreferrer">
          {url}
        </a>
      ),
    },
    {
      title: "订阅事件",
      dataIndex: "subscribed_events",
      key: "subscribed_events",
      render: (events: string[]) => (
        <Space>
          {events?.map((e) => (
            <Tag key={e}>{eventLabels[e] || e}</Tag>
          ))}
        </Space>
      ),
    },
    {
      title: "功能",
      key: "features",
      render: (_: unknown, record: GitIntegration) => (
        <Space>
          {record.auto_close_issue && (
            <Tag icon={<CheckCircleOutlined />} color="success">
              自动关闭
            </Tag>
          )}
          {record.auto_link_pr && (
            <Tag icon={<CheckCircleOutlined />} color="processing">
              PR 关联
            </Tag>
          )}
        </Space>
      ),
    },
    {
      title: "状态",
      dataIndex: "is_active",
      key: "is_active",
      render: (active: boolean) => (
        <Tag color={active ? "success" : "default"}>
          {active ? "启用" : "禁用"}
        </Tag>
      ),
    },
    {
      title: "操作",
      key: "actions",
      render: (_: unknown, record: GitIntegration) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Button
            type="link"
            size="small"
            icon={<ReloadOutlined />}
            onClick={() => handleRegenerateSecret(record.id)}
          >
            重置密钥
          </Button>
          <Popconfirm
            title="确定删除此集成配置？"
            onConfirm={() => handleDelete(record.id)}
          >
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Card
        title="Git Webhook 集成"
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
            添加集成
          </Button>
        }
      >
        <Alert
          message="配置说明"
          description={
            <div>
              <p>1. 添加集成后，将 Webhook URL 和 Secret 配置到 Git 平台（GitHub/Gitea/Forgejo）</p>
              <p>2. Commit message 中使用 <code>fix #123</code>、<code>close #123</code> 可自动关闭 Issue</p>
              <p>3. PR 标题/描述中使用 <code>plan #123</code> 可关联 Plan，合并时自动更新 Plan 状态</p>
            </div>
          }
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />

        <Table
          columns={columns}
          dataSource={integrations}
          rowKey="id"
          loading={loading}
          pagination={false}
        />
      </Card>

      {/* 创建/编辑 Modal */}
      <Modal
        title={editingIntegration ? "编辑集成配置" : "添加集成配置"}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => setModalVisible(false)}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="platform"
            label="Git 平台"
            rules={[{ required: true, message: "请选择平台" }]}
          >
            <Select disabled={!!editingIntegration}>
              {Object.entries(platformLabels).map(([key, cfg]) => (
                <Option key={key} value={key}>
                  {cfg.icon} {cfg.label}
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="repo_url"
            label="仓库 URL"
            rules={[{ required: true, message: "请输入仓库 URL" }]}
            extra="例如: https://github.com/owner/repo"
          >
            <Input placeholder="https://github.com/owner/repo" />
          </Form.Item>

          {!editingIntegration && (
            <Form.Item
              name="webhook_secret"
              label="Webhook Secret"
              rules={[
                { required: true, message: "请输入 Secret" },
                { min: 16, message: "Secret 至少 16 位" },
              ]}
              extra="用于验证 Webhook 请求的签名，至少 16 位"
            >
              <Input.Password placeholder="输入 Webhook Secret" />
            </Form.Item>
          )}

          {editingIntegration && (
            <Form.Item
              name="webhook_secret"
              label="Webhook Secret（留空保持不变）"
              extra="如需更新，请输入新的 Secret（至少 16 位）"
            >
              <Input.Password placeholder="输入新的 Webhook Secret" />
            </Form.Item>
          )}

          <Form.Item
            name="subscribed_events"
            label="订阅事件"
            rules={[{ required: true, message: "请选择订阅事件" }]}
          >
            <Select mode="multiple">
              <Option value="push">代码推送 (push)</Option>
              <Option value="pull_request">Pull Request</Option>
              <Option value="issues">Issues</Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="auto_close_issue"
            label="自动关闭 Issue"
            valuePropName="checked"
            extra="Commit message 中包含 fix/close/resolve #issue_id 时自动关闭 Issue"
          >
            <Switch />
          </Form.Item>

          <Form.Item
            name="auto_link_pr"
            label="PR 关联 Plan"
            valuePropName="checked"
            extra="PR 标题/描述中包含 plan #id 时自动关联，合并时更新 Plan 状态"
          >
            <Switch />
          </Form.Item>
        </Form>
      </Modal>

      {/* Webhook 信息 Modal */}
      {editingIntegration && (
        <Modal
          title="Webhook 配置信息"
          open={false}
          footer={null}
        >
          <Descriptions column={1} bordered>
            <Descriptions.Item label="Webhook URL">
              <Space>
                <Text code>{window.location.origin}/api/v1{editingIntegration.webhook_url}</Text>
                <Button
                  type="text"
                  icon={<CopyOutlined />}
                  onClick={() =>
                    copyToClipboard(
                      `${window.location.origin}/api/v1${editingIntegration.webhook_url}`
                    )
                  }
                />
              </Space>
            </Descriptions.Item>
          </Descriptions>
        </Modal>
      )}

      {/* 新生成 Secret Modal */}
      <Modal
        title="新的 Webhook Secret"
        open={secretModalVisible}
        onOk={() => setSecretModalVisible(false)}
        onCancel={() => setSecretModalVisible(false)}
      >
        <Alert
          message="请保存此 Secret"
          description="此 Secret 仅显示一次，请立即复制到 Git 平台的 Webhook 配置中。"
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
        />
        <Input.Group compact>
          <Input
            style={{ width: "calc(100% - 40px)" }}
            value={generatedSecret}
            readOnly
          />
          <Button
            type="primary"
            icon={<CopyOutlined />}
            onClick={() => copyToClipboard(generatedSecret)}
          />
        </Input.Group>
      </Modal>
    </div>
  );
}
