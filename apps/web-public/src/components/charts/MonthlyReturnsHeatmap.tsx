'use client';

import { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import { useTheme } from 'next-themes';

interface MonthlyReturn {
  year: number;
  month: number; // 1-12
  value: number; // percentage
}

interface MonthlyReturnsHeatmapProps {
  data: MonthlyReturn[];
  height?: number;
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

export function MonthlyReturnsHeatmap({ data, height = 320 }: MonthlyReturnsHeatmapProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const { resolvedTheme } = useTheme();

  useEffect(() => {
    if (!svgRef.current || !containerRef.current || data.length === 0) return;

    const isDark = resolvedTheme === 'dark';
    const width = containerRef.current.clientWidth;
    const margin = { top: 30, right: 20, bottom: 20, left: 50 };
    const innerW = width - margin.left - margin.right;
    const innerH = height - margin.top - margin.bottom;

    const years = [...new Set(data.map((d) => d.year))].sort();
    const cellW = innerW / 12;
    const cellH = Math.min(innerH / years.length, 36);

    const maxAbs = d3.max(data, (d) => Math.abs(d.value)) || 10;
    const colorScale = d3
      .scaleSequential()
      .domain([-maxAbs, maxAbs])
      .interpolator(d3.interpolateRdYlGn);

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();
    svg.attr('width', width).attr('height', height);

    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

    // Month labels
    g.selectAll('.month-label')
      .data(MONTHS)
      .enter()
      .append('text')
      .attr('x', (_, i) => i * cellW + cellW / 2)
      .attr('y', -10)
      .attr('text-anchor', 'middle')
      .attr('fill', isDark ? '#94a3b8' : '#64748b')
      .attr('font-size', '11px')
      .text((d) => d);

    // Year labels
    g.selectAll('.year-label')
      .data(years)
      .enter()
      .append('text')
      .attr('x', -8)
      .attr('y', (_, i) => i * cellH + cellH / 2 + 4)
      .attr('text-anchor', 'end')
      .attr('fill', isDark ? '#94a3b8' : '#64748b')
      .attr('font-size', '11px')
      .text((d) => d);

    // Cells
    const cells = g
      .selectAll('.cell')
      .data(data)
      .enter()
      .append('g')
      .attr('transform', (d) => {
        const yi = years.indexOf(d.year);
        return `translate(${(d.month - 1) * cellW},${yi * cellH})`;
      });

    cells
      .append('rect')
      .attr('width', cellW - 2)
      .attr('height', cellH - 2)
      .attr('rx', 3)
      .attr('fill', (d) => colorScale(d.value))
      .attr('opacity', 0.85);

    cells
      .append('text')
      .attr('x', (cellW - 2) / 2)
      .attr('y', (cellH - 2) / 2 + 4)
      .attr('text-anchor', 'middle')
      .attr('fill', (d) => (Math.abs(d.value) > maxAbs * 0.6 ? '#fff' : isDark ? '#e2e8f0' : '#1e293b'))
      .attr('font-size', '10px')
      .attr('font-family', 'JetBrains Mono, monospace')
      .text((d) => `${d.value > 0 ? '+' : ''}${d.value.toFixed(1)}%`);
  }, [data, height, resolvedTheme]);

  return (
    <div ref={containerRef} className="w-full overflow-x-auto">
      <svg ref={svgRef} />
    </div>
  );
}
