'use client';

import { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import { useTheme } from 'next-themes';

interface SectorData {
  name: string;
  weight: number;
  changePct: number;
}

interface SectorTreemapProps {
  data?: SectorData[];
  height?: number;
}

const defaultData: SectorData[] = [
  { name: 'Financials', weight: 35.2, changePct: 1.8 },
  { name: 'Consumer', weight: 18.5, changePct: -0.4 },
  { name: 'Energy', weight: 15.3, changePct: 2.9 },
  { name: 'Materials', weight: 12.8, changePct: -1.2 },
  { name: 'Telecom', weight: 8.4, changePct: 0.6 },
  { name: 'Industrials', weight: 5.6, changePct: -0.3 },
  { name: 'Real Estate', weight: 2.8, changePct: 1.1 },
  { name: 'Health Care', weight: 1.4, changePct: 0.8 },
];

export function SectorTreemap({ data = defaultData, height = 320 }: SectorTreemapProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const { resolvedTheme } = useTheme();

  useEffect(() => {
    if (!svgRef.current || !containerRef.current || data.length === 0) return;

    const isDark = resolvedTheme === 'dark';
    const width = containerRef.current.clientWidth;

    const maxAbs = d3.max(data, (d) => Math.abs(d.changePct)) || 5;
    const colorScale = d3
      .scaleSequential()
      .domain([-maxAbs, maxAbs])
      .interpolator(d3.interpolateRdYlGn);

    const root = d3
      .hierarchy({ children: data } as { children: SectorData[] })
      .sum((d) => (d as unknown as SectorData).weight || 0);

    d3.treemap<{ children: SectorData[] }>()
      .size([width, height])
      .padding(2)
      .round(true)(root);

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();
    svg.attr('width', width).attr('height', height);

    type TreeNode = d3.HierarchyRectangularNode<unknown> & { data: unknown };
    const leaves = root.leaves() as TreeNode[];

    const groups = svg
      .selectAll('g')
      .data(leaves)
      .enter()
      .append('g')
      .attr('transform', (d) => `translate(${d.x0},${d.y0})`);

    groups
      .append('rect')
      .attr('width', (d) => d.x1 - d.x0)
      .attr('height', (d) => d.y1 - d.y0)
      .attr('rx', 4)
      .attr('fill', (d) => colorScale((d.data as SectorData).changePct))
      .attr('opacity', 0.85);

    groups
      .append('text')
      .attr('x', (d) => (d.x1 - d.x0) / 2)
      .attr('y', (d) => (d.y1 - d.y0) / 2 - 4)
      .attr('text-anchor', 'middle')
      .attr('fill', isDark ? '#f1f5f9' : '#0f172a')
      .attr('font-size', (d) => ((d.x1 - d.x0) > 80 ? '12px' : '9px'))
      .attr('font-weight', '500')
      .text((d) => (d.data as SectorData).name);

    groups
      .append('text')
      .attr('x', (d) => (d.x1 - d.x0) / 2)
      .attr('y', (d) => (d.y1 - d.y0) / 2 + 12)
      .attr('text-anchor', 'middle')
      .attr('fill', isDark ? '#94a3b8' : '#475569')
      .attr('font-size', '10px')
      .attr('font-family', 'JetBrains Mono, monospace')
      .text((d) => {
        const sd = d.data as SectorData;
        return `${sd.weight.toFixed(1)}% | ${sd.changePct > 0 ? '+' : ''}${sd.changePct.toFixed(1)}%`;
      });
  }, [data, height, resolvedTheme]);

  return (
    <div ref={containerRef} className="w-full overflow-x-auto" aria-label="Sector treemap">
      <svg ref={svgRef} />
    </div>
  );
}
