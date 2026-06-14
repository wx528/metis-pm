import { useCallback, useMemo, useRef, useState, useEffect } from "react";
import ForceGraph2D from "react-force-graph-2d";
import type { GraphNode, GraphEdge } from "../../api/graph";
import NodePreview from "./NodePreview";

interface ForceGraphProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  onNodeClick?: (node: GraphNode) => void;
  width: number;
  height: number;
}

interface GraphNodeType {
  id: string;
  type: string;
  title: string;
  size: number;
  color: string;
  opacity: number;
  x?: number;
  y?: number;
  __data?: GraphNode;
}

export default function ForceGraph({ nodes, edges, onNodeClick, width, height }: ForceGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mousePosRef = useRef({ x: 0, y: 0 });
  const [hoveredNode, setHoveredNode] = useState<GraphNode | null>(null);
  const [hoverPos, setHoverPos] = useState({ x: 0, y: 0 });

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const handleMouseMove = (e: MouseEvent) => {
      mousePosRef.current = { x: e.clientX, y: e.clientY };
    };
    el.addEventListener("mousemove", handleMouseMove);
    return () => el.removeEventListener("mousemove", handleMouseMove);
  }, []);

  const graphNodes = useMemo(() =>
    nodes.map((node) => ({
      id: node.id,
      type: node.type,
      title: node.title,
      size: node.size,
      color: node.color,
      opacity: node.opacity,
      __data: node,
    })),
    [nodes]
  );

  const graphLinks = useMemo(() =>
    edges.map((edge) => ({
      source: edge.source,
      target: edge.target,
    })),
    [edges]
  );

  const handleNodeClick = useCallback((node: GraphNodeType) => {
    if (node.__data && onNodeClick) {
      onNodeClick(node.__data);
    }
  }, [onNodeClick]);

  const handleNodeHover = useCallback((node: GraphNodeType | null) => {
    setHoveredNode(node?.__data || null);
    if (node) {
      setHoverPos({ ...mousePosRef.current });
    }
  }, []);

  const nodeCanvasObject = useCallback((node: GraphNodeType, ctx: CanvasRenderingContext2D) => {
    const size = node.size;
    const x = node.x || 0;
    const y = node.y || 0;

    ctx.globalAlpha = node.opacity;

    if (node.type === "milestone") {
      ctx.beginPath();
      ctx.arc(x, y, size, 0, 2 * Math.PI);
      ctx.strokeStyle = node.color;
      ctx.lineWidth = 2;
      ctx.setLineDash([5, 3]);
      ctx.stroke();
      ctx.setLineDash([]);
    } else {
      ctx.beginPath();
      ctx.arc(x, y, size / 2, 0, 2 * Math.PI);
      ctx.fillStyle = node.color;
      ctx.fill();

      if (node.opacity < 0.5) {
        ctx.strokeStyle = "#888";
        ctx.lineWidth = 1;
        ctx.setLineDash([3, 2]);
        ctx.stroke();
        ctx.setLineDash([]);
      }
    }

    ctx.globalAlpha = 1;
  }, []);

  const nodePointerAreaPaint = useCallback((node: GraphNodeType, color: string, ctx: CanvasRenderingContext2D) => {
    const radius = node.type === "milestone" ? node.size : node.size / 2;
    ctx.beginPath();
    ctx.arc(node.x || 0, node.y || 0, radius, 0, 2 * Math.PI);
    ctx.fillStyle = color;
    ctx.fill();
  }, []);

  return (
    <div ref={containerRef}>
      <ForceGraph2D
        width={width}
        height={height}
        graphData={{ nodes: graphNodes, links: graphLinks }}
        nodeCanvasObject={nodeCanvasObject as any}
        nodePointerAreaPaint={nodePointerAreaPaint as any}
        onNodeClick={handleNodeClick}
        onNodeHover={handleNodeHover}
        onBackgroundClick={() => {}}
        linkColor={() => "rgba(100, 100, 100, 0.3)"}
        linkWidth={1}
        linkDirectionalArrowLength={0}
        d3AlphaDecay={0.02}
        d3VelocityDecay={0.3}
        cooldownTicks={100}
      />
      {hoveredNode && (
        <NodePreview node={hoveredNode} x={hoverPos.x} y={hoverPos.y} />
      )}
    </div>
  );
}
