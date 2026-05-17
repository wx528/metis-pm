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
import { Select, Spin, message, Space } from "antd";
import { issuesApi } from "../api/issues";
import { milestonesApi } from "../api/milestones";
import { useProject } from "../hooks/useProject";
import BoardColumn from "../components/BoardColumn";
import IssueCard from "../components/IssueCard";

interface IssueItem {
  id: number;
  title: string;
  priority: string;
  status: string;
  source: string;
  assignee: string | null;
  milestone_id: number | null;
  issue_type: string;
  project_id: number | null;
}

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
  const [issues, setIssues] = useState<IssueItem[]>([]);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [milestones, setMilestones] = useState<Milestone[]>([]);
  const [filterMilestone, setFilterMilestone] = useState<number | undefined>();
  const [deferTarget, setDeferTarget] = useState<{ issueId: number; milestoneId: number } | null>(null);
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
      setIssues(res.data.items as unknown as IssueItem[]);
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
      // 自动选第一个 milestone 并延迟
      const targetMilestone = milestones[0];
      setDeferTarget({ issueId, milestoneId: targetMilestone.id });
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

  // 处理 defer
  useEffect(() => {
    if (!deferTarget) return;
    const doDefer = async () => {
      const { issueId, milestoneId } = deferTarget;
      const issue = issues.find((i) => i.id === issueId);
      if (!issue) { setDeferTarget(null); return; }

      setIssues((prev) => prev.map((i) => (i.id === issueId ? { ...i, status: "deferred" } : i)));
      try {
        await issuesApi.defer(issueId, milestoneId);
        messageApi.success(`Issue #${issueId} → deferred`);
      } catch {
        setIssues((prev) => prev.map((i) => (i.id === issueId ? { ...i, status: issue.status } : i)));
        messageApi.error("暂缓失败");
      }
      setDeferTarget(null);
    };
    doDefer();
  }, [deferTarget]);

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
    </div>
  );
}
