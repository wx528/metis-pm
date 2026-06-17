import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Card,
  Descriptions,
  Tag,
  Button,
  Modal,
  Form,
  Input,
  Select,
  message,
  Divider,
  Space,
  List,
  Avatar,
} from "antd";
import { ArrowLeftOutlined, UserOutlined, RobotOutlined } from "@ant-design/icons";
import { issuesApi } from "../api/issues";
import type { Issue, Comment } from "../api";

const { Option } = Select;

const priorityColors: Record<string, string> = {
  P0: "red",
  P1: "orange",
  P2: "blue",
  P3: "default",
};

const statusColors: Record<string, string> = {
  open: "blue",
  in_progress: "processing",
  review: "purple",
  deferred: "warning",
  closed: "success",
  cancelled: "default",
};

export default function IssueDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [issue, setIssue] = useState<Issue | null>(null);
  const [loading, setLoading] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [editForm] = Form.useForm();
  const [commentText, setCommentText] = useState("");

  const fetchIssue = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const res = await issuesApi.get(Number(id));
      setIssue(res.data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIssue();
  }, [id]);

  const handleUpdate = async (values: any) => {
    if (!id) return;
    try {
      await issuesApi.update(Number(id), values);
      message.success("更新成功");
      setEditOpen(false);
      fetchIssue();
    } catch {
      message.error("更新失败");
    }
  };

  const handleAddComment = async () => {
    if (!id || !commentText.trim()) return;
    try {
      await issuesApi.addComment(Number(id), { content: commentText.trim() });
      message.success("评论已添加");
      setCommentText("");
      fetchIssue();
    } catch {
      message.error("评论失败");
    }
  };

  if (!issue) return <div style={{ padding: 40 }}>加载中...</div>;

  return (
    <div>
      <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/issues")} style={{ marginBottom: 16 }}>
        返回
      </Button>

      <Card
        title={
          <Space>
            <Tag color={priorityColors[issue.priority]}>{issue.priority}</Tag>
            {issue.title}
          </Space>
        }
        extra={
          <Button type="primary" onClick={() => setEditOpen(true)}>
            编辑
          </Button>
        }
        loading={loading}
      >
        <Descriptions bordered column={2}>
          <Descriptions.Item label="状态">
            <Tag color={statusColors[issue.status]}>{issue.status}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="类型">{issue.issue_type}</Descriptions.Item>
          <Descriptions.Item label="负责人">{issue.assignee_role || "-"}</Descriptions.Item>
          <Descriptions.Item label="创建时间">{issue.created_at}</Descriptions.Item>
          <Descriptions.Item label="更新时间">{issue.updated_at}</Descriptions.Item>
        </Descriptions>

        <Divider />
        <h4>描述</h4>
        <div style={{ whiteSpace: "pre-wrap", color: "#555" }}>
          {issue.description || "无描述"}
        </div>

        <Divider />
        <h4>评论 ({(issue as any).comments?.length || 0})</h4>
        {(issue as any).comments?.length > 0 ? (
          <List
            dataSource={(issue as any).comments}
            renderItem={(c: Comment) => (
              <List.Item>
                <List.Item.Meta
                  avatar={
                    <Avatar
                      icon={c.author_role === "ai_agent" ? <RobotOutlined /> : <UserOutlined />}
                      style={{ backgroundColor: c.author_role === "ai_agent" ? "#722ed1" : "#1890ff" }}
                    />
                  }
                  title={
                    <span>
                      {c.author_role || "匿名"}
                      <span style={{ color: "#999", fontSize: 12, marginLeft: 8 }}>
                        {new Date(c.created_at).toLocaleString("zh-CN")}
                      </span>
                    </span>
                  }
                  description={c.content}
                />
              </List.Item>
            )}
          />
        ) : (
          <div style={{ color: "#999", textAlign: "center", padding: 16 }}>暂无评论</div>
        )}
        <div style={{ marginTop: 12, display: "flex", gap: 8 }}>
          <Input.TextArea
            rows={2}
            value={commentText}
            onChange={(e) => setCommentText(e.target.value)}
            placeholder="添加评论..."
          />
          <Button type="primary" onClick={handleAddComment} disabled={!commentText.trim()}>
            发送
          </Button>
        </div>
      </Card>

      <Modal title="编辑 Issue" open={editOpen} onCancel={() => setEditOpen(false)} onOk={() => editForm.submit()} width={600}>
        <Form form={editForm} onFinish={handleUpdate} layout="vertical" initialValues={issue}>
          <Form.Item name="title" label="标题" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item name="issue_type" label="类型">
            <Select>
              <Option value="bug">bug</Option>
              <Option value="feature">feature</Option>
              <Option value="task">task</Option>
              <Option value="improvement">improvement</Option>
              <Option value="documentation">documentation</Option>
            </Select>
          </Form.Item>
          <Form.Item name="status" label="状态">
            <Select>
              <Option value="open">open</Option>
              <Option value="in_progress">in_progress</Option>
              <Option value="review">review</Option>
              <Option value="closed">closed</Option>
              <Option value="cancelled">cancelled</Option>
            </Select>
          </Form.Item>
          <Form.Item name="priority" label="优先级">
            <Select>
              <Option value="P0">P0</Option>
              <Option value="P1">P1</Option>
              <Option value="P2">P2</Option>
              <Option value="P3">P3</Option>
            </Select>
          </Form.Item>
          <Form.Item name="assignee_role" label="负责人">
            <Input placeholder="指定负责人角色" />
          </Form.Item>
          <Form.Item name="labels" label="标签">
            <Input placeholder="逗号分隔，如: backend,urgent" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
