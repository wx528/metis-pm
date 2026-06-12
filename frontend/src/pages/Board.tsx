import { useState, useEffect, useCallback } from "react";
import {
  DndContext,
  DragOverlay,
  closestCorners,
  PointerSensor,
  useSensor,
  useSensors,
  type DragStartEvent,
  type DragEndEvent,

} from "@dnd-kit/core";
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { Select, Spin, message, Space, Modal, Input } from "antd";
import { issuesApi, type Issue } from "../api/issues";
import { milestonesApi } from "../api/milestones";
import { useProject } from "../hooks/useProject";
import BoardColumn from "../components/BoardColumn";
import IssueCard from "../components/IssueCard";

interface Milestone {
  id: number;
  title: string;
}

const COLUMNS = [
  { id: "open", title: "Open", color: "#1890ff" },
  { id: "in_progress", title: "In Progress", color: "#722ed1" },
  { id: "review", title: "Review", color: "#fa8c16" },
  { id: "deferred", title: "Deferred", color: "#faad14" },
  { id: "closed", title: "Closed", color: "#52c41a" },
];

const PRIORITY_COLORS: Record<string, string> = {
  P0: "red",
  P1: "orange",
  P2: "blue",
  P3: "default",
};

export default function Board() {
  const { currentProject } = useProject();
  const [loading, setLoading] = useState(true);
  const [issues, setIssues] = useState<Issue[]>([]);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [milestones, setMilestones] = useState<Milestone[]>([]);
  const [filterMilestone, setFilterMilestone] = useState<number | undefined>();
  const [deferModal, setDeferModal] = useState<{ issueId: number; open: boolean }>({ issueId: 0, open: false });
  const [deferMilestoneId, setDeferMilestoneId] = useState<number | undefined>();
  const [deferReason, setDeferReason] = useState("");
  const messageApi = message;

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } })
  );

  const fetchIssues = useCallback(async () => {
    if (!currentProject) return;
    setLoading(true);
    try {
      const res = await issuesApi.list({
        project_id: currentProject.id,
        milestone_id: filterMilestone,
        limit: 200,
      });
      setIssues(res.data.items);
    } finally {
      setLoading(false);
    }
  }, [currentProject, filterMilestone]);

  const fetchMilestones = useCallback(async () => {
    if (!currentProject) return;
    try {
      const res = await milestonesApi.list({ project_id: currentProject.id });
      setMilestones(res.data.map((m: any) => ({ id: m.id, title: m.title })));
    } catch {}
  }, [currentProject]);

  useEffect(() => {
    fetchIssues();
    fetchMilestones();
  }, [fetchIssues, fetchMilestones]);

  // 按列分组
  const columns = COLUMNS.map((col) => ({
    ...col,
    issues: issues.filter((i) => i.status === col.id),
  }));

  const handleDragStart = (event: DragStartEvent) => {
    setActiveId(event.active.id as number);
  };

  const handleDragEnd = async (event: DragEndEvent) => {
    setActiveId(null);
    const { active, over } = event;
    if (!over) return;

    const issueId = active.id as number;
    const issue = issues.find((i) => i.id === issueId);
    if (!issue) return;

    // over.id 可能是列 ID 或另一个 issue 的 ID
    let targetStatus: string | null = null;

    // 检查是否拖到了列上
    const colIds = COLUMNS.map((c) => c.id);
    if (colIds.includes(over.id as string)) {
      targetStatus = over.id as string;
    } else {
      // 拖到了另一个 issue 上，取该 issue 的 status
      const overIssue = issues.find((i) => i.id === over.id);
      if (overIssue) {
        targetStatus = overIssue.status;
      }
    }

    if (!targetStatus || targetStatus === issue.status) return;

    // Deferred 需要选 milestone
    if (targetStatus === "deferred") {
      if (milestones.length === 0) {
        messageApi.warning("请先创建里程碑");
        return;
      }
      // 弹窗让用户选择目标 milestone 和填写原因
      setDeferMilestoneId(milestones[0].id);
      setDeferReason("");
      setDeferModal({ issueId, open: true });
      return;
    }

    // 乐观更新
    setIssues((prev) => prev.map((i) => (i.id === issueId ? { ...i, status: targetStatus! } : i)));

    try {
      await issuesApi.update(issueId, { status: targetStatus });
      messageApi.success(`Issue #${issueId} → ${targetStatus}`);
    } catch {
      // 回滚
      setIssues((prev) => prev.map((i) => (i.id === issueId ? { ...i, status: issue.status } : i)));
      messageApi.error("状态更新失败");
    }
  };

  // 处理 defer 确认
  const handleDeferConfirm = async () => {
    const issueId = deferModal.issueId;
    if (!deferMilestoneId) {
      messageApi.warning("请选择目标里程碑");
      return;
    }
    const issue = issues.find((i) => i.id === issueId);
    if (!issue) { setDeferModal({ issueId: 0, open: false }); return; }

    setIssues((prev) => prev.map((i) => (i.id === issueId ? { ...i, status: "deferred" } : i)));
    setDeferModal({ issueId: 0, open: false });
    try {
      await issuesApi.defer(issueId, deferMilestoneId, deferReason || undefined);
      messageApi.success(`Issue #${issueId} → deferred`);
    } catch {
      setIssues((prev) => prev.map((i) => (i.id === issueId ? { ...i, status: issue.status } : i)));
      messageApi.error("暂缓失败");
    }
  };

  const activeIssue = activeId ? issues.find((i) => i.id === activeId) : null;

  if (loading) return <Spin size="large" style={{ display: "block", margin: "100px auto" }} />;

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>看板{currentProject ? ` — ${currentProject.name}` : ""}</h2>
        <Space>
          <span style={{ fontSize: 13, color: "#999" }}>里程碑筛选：</span>
          <Select
            value={filterMilestone}
            onChange={setFilterMilestone}
            allowClear
            placeholder="全部"
            style={{ width: 180 }}
            size="small"
          >
            {milestones.map((m) => (
              <Select.Option key={m.id} value={m.id}>{m.title}</Select.Option>
            ))}
          </Select>
        </Space>
      </div>

      <DndContext
        sensors={sensors}
        collisionDetection={closestCorners}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      >
        <div style={{ display: "flex", gap: 12, overflowX: "auto", paddingBottom: 8 }}>
          {columns.map((col) => (
            <BoardColumn key={col.id} id={col.id} title={col.title} color={col.color} count={col.issues.length}>
              <SortableContext items={col.issues.map((i) => i.id)} strategy={verticalListSortingStrategy}>
                {col.issues.map((issue) => (
                  <IssueCard key={issue.id} issue={issue} priorityColors={PRIORITY_COLORS} />
                ))}
              </SortableContext>
              {col.issues.length === 0 && (
                <div style={{ padding: "20px 0", textAlign: "center", color: "#ccc", fontSize: 12 }}>拖拽到此处</div>
              )}
            </BoardColumn>
          ))}
        </div>

        <DragOverlay>
          {activeIssue ? <IssueCard issue={activeIssue} priorityColors={PRIORITY_COLORS} isDragOverlay /> : null}
        </DragOverlay>
      </DndContext>

      <Modal
        title="暂缓 Issue"
        open={deferModal.open}
        onOk={handleDeferConfirm}
        onCancel={() => setDeferModal({ issueId: 0, open: false })}
        okText="确认暂缓"
        cancelText="取消"
      >
        <div style={{ marginBottom: 12 }}>
          <div style={{ marginBottom: 4, fontSize: 13, color: "#666" }}>目标里程碑</div>
          <Select
            value={deferMilestoneId}
            onChange={setDeferMilestoneId}
            style={{ width: "100%" }}
            placeholder="选择里程碑"
          >
            {milestones.map((m) => (
              <Select.Option key={m.id} value={m.id}>{m.title}</Select.Option>
            ))}
          </Select>
        </div>
        <div>
          <div style={{ marginBottom: 4, fontSize: 13, color: "#666" }}>暂缓原因（可选）</div>
          <Input.TextArea
            value={deferReason}
            onChange={(e) => setDeferReason(e.target.value)}
            rows={3}
            placeholder="填写暂缓原因..."
          />
        </div>
      </Modal>
    </div>
  );
}
