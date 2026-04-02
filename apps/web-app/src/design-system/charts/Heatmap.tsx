'use client';

import { useRef, useEffect, useState, useCallback } from 'react';
import * as d3 from 'd3';
import { cn } from '@/lib/utils';
import { Card } from '@/design-system/primitives/Card';
import { Skeleton } from '@/design-system/primitives/Skeleton';

export interface HeatmapNode {
  name: string;
  value: number;
  change: number;
  children?: HeatmapNode[];
}

interface HeatmapProps {
  data: HeatmapNode[];
  height?: number;
  onClick?: (name: string) => void;
  className?: string;
}

function getChangeColor(change: number): string {
  if (change <= -5) return '#991b1b';
  if (change <= -3) return '#b91c1c';
  if (change <= -1) return '#dc2626';
  if (change < 0) return '#ef4444';
  if (change === 0) return '#3f3f46';
  if (change < 1) return '#22c55e';
  if (change < 3) return '#16a34a';
  if (change < 5) return '#15803d';
  return '#166534';
}

function Heatmap({ data, height = 400, onClick, className }: HeatmapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const [width, setWidth] = useState(0);

  const render = useCallback(() => {
    const svg = svgRef.current;
    if (!svg || width === 0 || data.length === 0) return;

    const root = d3
      .hierarchy<HeatmapNode>({ name: 'root', value: 0, change: 0, children: data })
      .sum((d) => Math.abs(d.value) || 1)
      .sort((a, b) => (b.value ?? 0) - (a.value ?? 0));

    d3.treemap<HeatmapNode>().size([width, height]).padding(2).round(true)(root);

    const sel = d3.select(svg);
    sel.selectAll('*').remove();

    const leaves = root.leaves() as d3.HierarchyRectangularNode<HeatmapNode>[];

    const groups = sel
      .selectAll('g')
      .data(leaves)
      .join('g')
      .attr('transform', (d) => `translate(${d.x0},${d.y0})`)
      .style('cursor', onClick ? 'pointer' : 'default');

    if (onClick) {
      groups.on('click', (_, d) => onClick(d.data.name));
    }

    groups
      .append('rect')
      .attr('width', (d) => Math.max(0, d.x1 - d.x0))
      .attr('height', (d) => Math.max(0, d.y1 - d.y0))
      .attr('rx', 3)
      .attr('fill', (d) => getChangeColor(d.data.change));

    // Name labels
    groups
      .append('text')
      .attr('x', (d) => (d.x1 - d.x0) / 2)
      .attr('y', (d) => (d.y1 - d.y0) / 2 - 6)
      .attr('text-anchor', 'middle')
      .attr('dominant-baseline', 'middle')
      .attr('fill', '#fafafa')
      .attr('font-size', (d) => {
        const cellWidth = d.x1 - d.x0;
        return cellWidth < 60 ? '9px' : '11px';
      })
      .attr('font-weight', '600')
      .attr('font-family', "'Geist Sans', system-ui, sans-serif")
      .text((d) => {
        const cellWidth = d.x1 - d.x0;
        if (cellWidth < 30) return '';
        return d.data.name;
      });

    // Change % labels
    groups
      .append('text')
      .attr('x', (d) => (d.x1 - d.x0) / 2)
      .attr('y', (d) => (d.y1 - d.y0) / 2 + 8)
      .attr('text-anchor', 'middle')
      .attr('dominant-baseline', 'middle')
      .attr('fill', 'rgba(250,250,250,0.8)')
      .attr('font-size', '10px')
      .attr('font-family', "'Geist Mono', monospace")
      .text((d) => {
        const cellWidth = d.x1 - d.x0;
        if (cellWidth < 40) return '';
        const sign = d.data.change >= 0 ? '+' : '';
        return `${sign}${d.data.change.toFixed(1)}%`;
      });
  }, [data, width, height, onClick]);

  // Resize observer
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) setWidth(entry.contentRect.width);
    });

    observer.observe(container);
    setWidth(container.clientWidth);
    return () => observer.disconnect();
  }, []);

  // Re-render on data/dimensions change
  useEffect(() => {
    render();
  }, [render]);

  if (data.length === 0) {
    return (
      <Card className={cn('flex items-center justify-center p-4', className)} style={{ height }}>
        <p className="text-sm text-[var(--text-tertiary)]">No heatmap data available</p>
      </Card>
    );
  }

  return (
    <div
      ref={containerRef}
      className={cn('overflow-hidden rounded-lg border border-[var(--border-default)] bg-[var(--surface-0)]', className)}
      style={{ height }}
      aria-label="Sector heatmap"
      role="img"
    >
      <svg ref={svgRef} width={width} height={height} />
    </div>
  );
}

function HeatmapSkeleton({ height = 400, className }: { height?: number; className?: string }) {
  return (
    <Card className={cn('p-4', className)} style={{ height }}>
      <div className="grid h-full grid-cols-4 grid-rows-3 gap-1">
        {Array.from({ length: 12 }).map((_, i) => (
          <Skeleton key={i} className="h-full w-full rounded-sm" />
        ))}
      </div>
    </Card>
  );
}

export { Heatmap, HeatmapSkeleton };
