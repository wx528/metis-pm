import { Card, Empty } from "antd";

interface BurndownData {
  date: string;
  remaining: number;
}

interface BurndownProps {
  actual: BurndownData[];
  ideal: BurndownData[];
  loading?: boolean;
}

export default function BurndownChart({ actual, ideal, loading }: BurndownProps) {
  if (!actual || actual.length === 0) {
    return (
      <Card title="燃尽图" loading={loading}>
        <Empty description="暂无数据" />
      </Card>
    );
  }

  // 计算图表尺寸
  const width = 600;
  const height = 300;
  const padding = { top: 20, right: 20, bottom: 40, left: 50 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  // 计算数据范围
  const maxRemaining = Math.max(
    ...actual.map(d => d.remaining),
    ...ideal.map(d => d.remaining)
  );
  const maxDays = Math.max(actual.length, ideal.length);

  // 坐标转换函数
  const xScale = (index: number) => padding.left + (index / Math.max(1, maxDays - 1)) * chartWidth;
  const yScale = (value: number) => padding.top + chartHeight - (value / Math.max(1, maxRemaining)) * chartHeight;

  // 生成路径
  const actualPath = actual.map((d, i) => {
    const x = xScale(i);
    const y = yScale(d.remaining);
    return `${i === 0 ? 'M' : 'L'} ${x} ${y}`;
  }).join(' ');

  const idealPath = ideal.map((d, i) => {
    const x = xScale(i);
    const y = yScale(d.remaining);
    return `${i === 0 ? 'M' : 'L'} ${x} ${y}`;
  }).join(' ');

  // 生成Y轴刻度
  const yTicks = 5;
  const yTickValues = Array.from({ length: yTicks + 1 }, (_, i) => Math.round(maxRemaining * i / yTicks));

  // 生成X轴标签（每隔几天显示一个）
  const xLabelInterval = Math.max(1, Math.floor(maxDays / 6));
  const xLabels = actual.filter((_, i) => i % xLabelInterval === 0 || i === actual.length - 1);

  return (
    <Card title="燃尽图" loading={loading}>
      <svg width={width} height={height} style={{ maxWidth: '100%' }}>
        {/* 网格线 */}
        {yTickValues.map((value, i) => (
          <g key={`grid-${i}`}>
            <line
              x1={padding.left}
              y1={yScale(value)}
              x2={width - padding.right}
              y2={yScale(value)}
              stroke="#f0f0f0"
              strokeDasharray="2,2"
            />
            <text
              x={padding.left - 10}
              y={yScale(value) + 4}
              textAnchor="end"
              fontSize="12"
              fill="#999"
            >
              {value}
            </text>
          </g>
        ))}

        {/* X轴标签 */}
        {xLabels.map((d, i) => {
          const originalIndex = actual.indexOf(d);
          return (
            <text
              key={`xlabel-${i}`}
              x={xScale(originalIndex)}
              y={height - 10}
              textAnchor="middle"
              fontSize="11"
              fill="#999"
            >
              {d.date.slice(5)} {/* 显示 MM-DD */}
            </text>
          );
        })}

        {/* 理想线 */}
        <path
          d={idealPath}
          fill="none"
          stroke="#d9d9d9"
          strokeWidth="2"
          strokeDasharray="5,5"
        />

        {/* 实际线 */}
        <path
          d={actualPath}
          fill="none"
          stroke="#1890ff"
          strokeWidth="2"
        />

        {/* 数据点 */}
        {actual.map((d, i) => (
          <circle
            key={`point-${i}`}
            cx={xScale(i)}
            cy={yScale(d.remaining)}
            r="3"
            fill="#1890ff"
          />
        ))}

        {/* 图例 */}
        <g transform={`translate(${width - 150}, 10)`}>
          <line x1="0" y1="0" x2="20" y2="0" stroke="#1890ff" strokeWidth="2" />
          <text x="25" y="4" fontSize="12" fill="#666">实际</text>
          <line x1="60" y1="0" x2="80" y2="0" stroke="#d9d9d9" strokeWidth="2" strokeDasharray="5,5" />
          <text x="85" y="4" fontSize="12" fill="#666">理想</text>
        </g>

        {/* 轴标签 */}
        <text
          x={padding.left - 30}
          y={padding.top + chartHeight / 2}
          textAnchor="middle"
          fontSize="12"
          fill="#666"
          transform={`rotate(-90, ${padding.left - 30}, ${padding.top + chartHeight / 2})`}
        >
          剩余 Issue
        </text>
      </svg>
    </Card>
  );
}
