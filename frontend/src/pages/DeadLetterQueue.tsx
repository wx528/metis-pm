import { useState, useEffect, useCallback } from "react";
import {
  Table, Button, Tag, Space, Card, Modal, Descriptions, Statistic, Row, Col, message, Popconfirm,
} from "antd";
import {
  ReloadOutlined, RedoOutlined, DeleteOutlined, WarningOutlined,
} from "@ant-design/icons";
import { monitoringApi } from "../api/monitoring";
import type { DeadLetterMessage, QueueStats } from "../api/monitoring";

export default function DeadLetterQueue() {
  const [messages, setMessages] = useState<DeadLetterMessage[]>([]);
  const [total, setTotal] = useState(0);
  const [stats, setStats] = useState<QueueStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<DeadLetterMessage | null>(null);
  const [page, setPage] = useState(1);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [dlData, statsData] = await Promise.all([
        monitoringApi.listDeadLetter({ skip: (page - 1) * 20, limit: 20 }),
        monitoringApi.getQueueStats(),
      ]);
      setMessages(dlData.items);
      setTotal(dlData.total);
      setStats(statsData);
    } catch {
      message.error("加载失败");
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleRetry = async (id: number) => {
    try {
      await monitoringApi.retryDeadLetter(id);
      message.success("已移回主队列");
      loadData();
    } catch {
      message.error("重试失败");
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await monitoringApi.deleteDeadLetter(id);
      message.success("已删除");
      loadData();
    } catch {
      message.error("删除失败");
    }
  };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>死信队列</h2>
        <Button icon={<ReloadOutlined />} onClick={loadData}>刷新</Button>
      </div>

      {stats && (
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={6}>
            <Card size="small">
              <Statistic title="主队列待处理" value={stats.queue.pending} />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic title="主队列总数" value={stats.queue.total} />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title="死信消息"
                value={stats.dead_letter}
                valueStyle={stats.dead_letter > 0 ? { color: "#fa541c" } : undefined}
                prefix={stats.dead_letter > 0 ? <WarningOutlined /> : undefined}
              />
            </Card>
          </Col>
        </Row>
      )}

      <Table
        rowKey="id"
        dataSource={messages}
        loading={loading}
        size="small"
        pagination={{
          current: page,
          total,
          pageSize: 20,
          onChange: setPage,
          showTotal: (t) => `共 ${t} 条`,
        }}
        onRow={(record) => ({
          onClick: () => setSelected(record),
          style: { cursor: "pointer", background: selected?.id === record.id ? "#f0f5ff" : undefined },
        })}
        columns={[
          {
            title: "ID",
            dataIndex: "id",
            width: 60,
          },
          {
            title: "消息摘要",
            render: (_, record) => {
              const p = record.payload || {};
              const title = p.title || p.type || JSON.stringify(p).slice(0, 50);
              return <span style={{ fontSize: 13 }}>{title}</span>;
            },
          },
          {
            title: "重试次数",
            dataIndex: "retry_count",
            width: 80,
            render: (v: number) => <Tag color={v >= 3 ? "red" : "orange"}>{v}</Tag>,
          },
          {
            title: "错误",
            dataIndex: "error",
            ellipsis: true,
            render: (v: string) => (
              <span style={{ fontSize: 12, color: "#ff4d4f" }} title={v}>
                {v || "-"}
              </span>
            ),
          },
          {
            title: "移入时间",
            dataIndex: "moved_at",
            width: 160,
            render: (v: string) => v ? new Date(v).toLocaleString() : "-",
          },
          {
            title: "操作",
            width: 120,
            render: (_, record) => (
              <Space size={4}>
                <Button
                  size="small"
                  type="link"
                  icon={<RedoOutlined />}
                  onClick={(e) => { e.stopPropagation(); handleRetry(record.id); }}
                >
                  重试
                </Button>
                <Popconfirm title="确定删除？" onConfirm={() => handleDelete(record.id)}>
                  <Button
                    size="small"
                    type="link"
                    danger
                    icon={<DeleteOutlined />}
                    onClick={(e) => e.stopPropagation()}
                  >
                    删除
                  </Button>
                </Popconfirm>
              </Space>
            ),
          },
        ]}
      />

      <Modal
        title={`死信消息 #${selected?.id || ""}`}
        open={!!selected}
        onCancel={() => setSelected(null)}
        footer={null}
        width={560}
      >
        {selected && (
          <Descriptions column={1} size="small">
            <Descriptions.Item label="ID">{selected.id}</Descriptions.Item>
            <Descriptions.Item label="原始状态">{selected.original_status}</Descriptions.Item>
            <Descriptions.Item label="重试次数">{selected.retry_count}</Descriptions.Item>
            <Descriptions.Item label="错误">{selected.error || "-"}</Descriptions.Item>
            <Descriptions.Item label="移入时间">{selected.moved_at ? new Date(selected.moved_at).toLocaleString() : "-"}</Descriptions.Item>
            <Descriptions.Item label="消息内容">
              <pre style={{ fontSize: 12, maxHeight: 200, overflow: "auto", margin: 0 }}>
                {JSON.stringify(selected.payload, null, 2)}
              </pre>
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </div>
  );
}
