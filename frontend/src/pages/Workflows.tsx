import { useEffect, useState } from "react";
import {
  Table, Button, Tag, Space, Modal, Form, Input, Select, message, Spin,
  Card, Steps, Timeline, Empty, Descriptions, Popconfirm,
} from "antd";
import {
  PlusOutlined, PlayCircleOutlined, ThunderboltOutlined,
  CheckCircleOutlined, CloseCircleOutlined,
} from "@ant-design/icons";
import { workflowsApi, type Workflow, type WorkflowStep, type WorkflowRun } from "../api/workflows";
import { useProject } from "../hooks/useProject";

const TRIGGER_LABELS: Record<string, string> = {
  on_issue_created: "Issue 创建时",
  on_plan_approved: "Plan 审批时",
  on_schedule: "定时触发",
  manual: "手动触发",
};

const TRIGGER_COLORS: Record<string, string> = {
  on_issue_created: "blue",
  on_plan_approved: "green",
  on_schedule: "orange",
  manual: "default",
};

const STEP_TYPE_LABELS: Record<string, string> = {
  create_issue: "创建 Issue",
  update_issue: "更新 Issue",
  notify: "发送通知",
  wait_approval: "等待审批",
  propose_plan: "提议 Plan",
};

const STEP_TYPE_COLORS: Record<string, string> = {
  create_issue: "blue",
  update_issue: "purple",
  notify: "cyan",
  wait_approval: "orange",
  propose_plan: "green",
};

const RUN_STATUS_COLORS: Record<string, string> = {
  running: "processing",
  completed: "success",
  failed: "error",
  waiting_approval: "warning",
  aborted: "default",
};

export default function Workflows() {
  const { currentProject } = useProject();
  const [loading, setLoading] = useState(true);
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [runs, setRuns] = useState<WorkflowRun[]>([]);
  const [selectedWf, setSelectedWf] = useState<Workflow | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [form] = Form.useForm();
  const msgApi = message;

  const fetch = async () => {
    if (!currentProject) return;
    setLoading(true);
    try {
      const [wfRes, runRes] = await Promise.all([
        workflowsApi.list({ project_id: currentProject.id }),
        workflowsApi.listRuns({ limit: 20 }),
      ]);
      setWorkflows(wfRes);
      setRuns(runRes.filter((r) => {
        // 过滤当前项目的 runs
        const wf = wfRes.find((w) => w.id === r.workflow_id);
        return wf !== undefined;
      }));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetch(); }, [currentProject]);

  const handleCreate = async () => {
    try {
      const values = await form.validateFields();
      const steps = values.steps || [];
      await workflowsApi.create({
        name: values.name,
        description: values.description,
        trigger: values.trigger,
        project_id: currentProject?.id,
        steps,
      });
      msgApi.success("工作流创建成功");
      setCreateOpen(false);
      form.resetFields();
      fetch();
    } catch {}
  };

  const handleTrigger = async (id: number) => {
    try {
      const run = await workflowsApi.trigger(id);
      msgApi.success(`已触发! Run #${run.id} (${run.status})`);
      fetch();
    } catch {
      msgApi.error("触发失败");
    }
  };

  const handleResume = async (runId: number, approved: boolean) => {
    try {
      await workflowsApi.resume(runId, approved);
      msgApi.success(approved ? "已通过审批" : "已拒绝");
      fetch();
    } catch {
      msgApi.error("操作失败");
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await workflowsApi.delete(id);
      msgApi.success("已删除");
      setSelectedWf(null);
      fetch();
    } catch {
      msgApi.error("删除失败");
    }
  };

  if (loading) return <Spin size="large" style={{ display: "block", margin: "100px auto" }} />;

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>工作流{currentProject ? ` — ${currentProject.name}` : ""}</h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>新建工作流</Button>
      </div>

      <div style={{ display: "flex", gap: 16 }}>
        {/* 左侧：工作流列表 */}
        <div style={{ flex: 1 }}>
          <Table
            rowKey="id"
            dataSource={workflows}
            size="small"
            onRow={(record) => ({
              onClick: () => setSelectedWf(record),
              style: { cursor: "pointer", background: selectedWf?.id === record.id ? "#f0f5ff" : undefined },
            })}
            pagination={false}
            columns={[
              {
                title: "名称",
                dataIndex: "name",
                render: (text: string, record: Workflow) => (
                  <Space>
                    <ThunderboltOutlined />
                    <span>{text}</span>
                  </Space>
                ),
              },
              {
                title: "触发",
                dataIndex: "trigger",
                width: 120,
                render: (v: string) => <Tag color={TRIGGER_COLORS[v]}>{TRIGGER_LABELS[v] || v}</Tag>,
              },
              {
                title: "状态",
                dataIndex: "status",
                width: 80,
                render: (v: string) => <Tag color={v === "active" ? "green" : "default"}>{v}</Tag>,
              },
              {
                title: "步骤",
                width: 60,
                render: (_, record: Workflow) => record.steps?.length || 0,
              },
              {
                title: "操作",
                width: 80,
                render: (_, record: Workflow) => (
                  <Button
                    size="small"
                    type="link"
                    icon={<PlayCircleOutlined />}
                    onClick={(e) => { e.stopPropagation(); handleTrigger(record.id); }}
                  >
                    触发
                  </Button>
                ),
              },
            ]}
          />

          {/* 执行记录 */}
          <Card title="执行记录" size="small" style={{ marginTop: 16 }}>
            {runs.length === 0 ? (
              <Empty description="暂无执行记录" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            ) : (
              <Timeline
                items={runs.map((run) => ({
                  color: RUN_STATUS_COLORS[run.status] === "error" ? "red" : RUN_STATUS_COLORS[run.status] === "success" ? "green" : "blue",
                  children: (
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <div>
                        <Tag color={RUN_STATUS_COLORS[run.status]}>{run.status}</Tag>
                        <span style={{ fontSize: 13 }}>{run.workflow_name || `WF#${run.workflow_id}`}</span>
                        <span style={{ fontSize: 11, color: "#999", marginLeft: 8 }}>by {run.triggered_by || "?"}</span>
                      </div>
                      {run.status === "waiting_approval" && (
                        <Space size={4}>
                          <Button size="small" type="primary" icon={<CheckCircleOutlined />} onClick={() => handleResume(run.id, true)}>通过</Button>
                          <Button size="small" danger icon={<CloseCircleOutlined />} onClick={() => handleResume(run.id, false)}>拒绝</Button>
                        </Space>
                      )}
                    </div>
                  ),
                }))}
            )}
          </Card>
        </div>

        {/* 右侧：工作流详情 */}
        <div style={{ width: 360 }}>
          {selectedWf ? (
            <Card
              title={selectedWf.name}
              size="small"
              extra={
                <Popconfirm title="确定删除此工作流？" onConfirm={() => handleDelete(selectedWf.id)}>
                  <Button size="small" danger>删除</Button>
                </Popconfirm>
              }
            >
              <Descriptions column={1} size="small">
                <Descriptions.Item label="触发方式">
                  <Tag color={TRIGGER_COLORS[selectedWf.trigger]}>{TRIGGER_LABELS[selectedWf.trigger]}</Tag>
                </Descriptions.Item>
                <Descriptions.Item label="状态">
                  <Tag color={selectedWf.status === "active" ? "green" : "default"}>{selectedWf.status}</Tag>
                </Descriptions.Item>
                {selectedWf.description && (
                  <Descriptions.Item label="描述">{selectedWf.description}</Descriptions.Item>
                )}
                {selectedWf.created_by && (
                  <Descriptions.Item label="创建者">{selectedWf.created_by}</Descriptions.Item>
                )}
              </Descriptions>

              <div style={{ marginTop: 12 }}>
                <div style={{ fontWeight: 600, marginBottom: 8, fontSize: 13 }}>步骤流程</div>
                {selectedWf.steps && selectedWf.steps.length > 0 ? (
                  <Steps
                    direction="vertical"
                    size="small"
                    current={-1}
                    items={selectedWf.steps.sort((a, b) => a.sort_order - b.sort_order).map((step) => ({
                      title: step.name || STEP_TYPE_LABELS[step.step_type] || step.step_type,
                      description: (
                        <Space size={4}>
                          <Tag color={STEP_TYPE_COLORS[step.step_type]} style={{ fontSize: 10 }}>
                            {STEP_TYPE_LABELS[step.step_type] || step.step_type}
                          </Tag>
                          <span style={{ fontSize: 11, color: "#999" }}>超时 {step.timeout_seconds}s</span>
                        </Space>
                      ),
                    }))}
                  />
                ) : (
                  <Empty description="无步骤" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                )}
              </div>
            </Card>
          ) : (
            <Card size="small">
              <Empty description="选择一个工作流查看详情" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            </Card>
          )}
        </div>
      </div>

      {/* 创建弹窗 */}
      <Modal
        title="新建工作流"
        open={createOpen}
        onOk={handleCreate}
        onCancel={() => { setCreateOpen(false); form.resetFields(); }}
        width={560}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="名称" rules={[{ required: true }]}>
            <Input placeholder="如：Bug 自动处理流" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="trigger" label="触发方式" initialValue="manual">
            <Select>
              <Select.Option value="manual">手动触发</Select.Option>
              <Select.Option value="on_issue_created">Issue 创建时</Select.Option>
              <Select.Option value="on_plan_approved">Plan 审批时</Select.Option>
            </Select>
          </Form.Item>
        </Form>
        <div style={{ color: "#999", fontSize: 12, marginTop: 8 }}>
          创建后可在详情页添加步骤。也可通过 MCP 工具创建含步骤的完整工作流。
        </div>
      </Modal>
    </div>
  );
}
