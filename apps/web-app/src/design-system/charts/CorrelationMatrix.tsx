'use client';

import { useRef, useEffect, useState, useCallback } from 'react';
import * as d3 from 'd3';
import { cn } from '@/lib/utils';
import { Card } from '@/design-system/primitives/Card';
import { Skeleton } from '@/design-system/primitives/Skeleton';

interface CorrelationMatrixProps {
  symbols: string[];
  matrix: number[][];
  height?: number;
  className?: string;
}

function CorrelationMatrix({ symbols, matrix, height = 400, className }: CorrelationMatrixProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(0);

  const render = useCallback(() => {
    const svg = svgRef.current;
    if (!svg || width === 0 || symbols.length === 0) return;

    const sel = d3.select(svg);
    sel.selectAll('*').remove();

    const n = symbols.length;
    const margin = { top: 40, right: 10, bottom: 10, left: 60 };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;
    const cellSize = Math.min(innerWidth / n, innerHeight / n);

    const colorScale = d3
      .scaleLinear<string>()
      .domain([-1, 0, 1])
      .range(['#ef4444', '#3f3f46', '#2563eb']);

    const g = sel.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

    // Column labels
    g.selectAll('.col-label')
      .data(symbols)
      .join('text')
      .attr('class', 'col-label')
      .attr('x', (_, i) => i * cellSize + cellSize / 2)
      .attr('y', -8)
      .attr('text-anchor', 'middle')
      .attr('fill', '#a1a1aa')
      .attr('font-size', Math.min(11, cellSize * 0.35) + 'px')
      .attr('font-family', "'Geist Mono', monospace")
      .text((d) => d);

    // Row labels
    g.selectAll('.row-label')
      .data(symbols)
      .join('text')
      .attr('class', 'row-label')
      .attr('x', -8)
      .attr('y', (_, i) => i * cellSize + cellSize / 2)
      .attr('text-anchor', 'end')
      .attr('dominant-baseline', 'middle')
      .attr('fill', '#a1a1aa')
      .attr('font-size', Math.min(11, cellSize * 0.35) + 'px')
      .attr('font-family', "'Geist Mono', monospace")
      .text((d) => d);

    // Cells
    for (let row = 0; row < n; row++) {
      for (let col = 0; col < n; col++) {
        const val = matrix[row]?.[col] ?? 0;

        g.append('rect')
          .attr('x', col * cellSize)
          .attr('y', row * cellSize)
          .attr('width', cellSize - 1)
          .attr('height', cellSize - 1)
          .attr('rx', 2)
          .attr('fill', colorScale(val))
          .attr('opacity', 0.8 + Math.abs(val) * 0.2)
          .style('cursor', 'pointer')
          .on('mouseenter', function (event) {
            d3.select(this).attr('opacity', 1).attr('stroke', '#fafafa').attr('stroke-width', 1);
            const tooltip = tooltipRef.current;
            if (tooltip) {
              tooltip.style.display = 'block';
              tooltip.style.left = `${event.offsetX + 12}px`;
              tooltip.style.top = `${event.offsetY - 30}px`;
              tooltip.textContent = `${symbols[row]} / ${symbols[col]}: ${val.toFixed(3)}`;
            }
          })
          .on('mousemove', function (event) {
            const tooltip = tooltipRef.current;
            if (tooltip) {
              tooltip.style.left = `${event.offsetX + 12}px`;
              tooltip.style.top = `${event.offsetY - 30}px`;
            }
          })
          .on('mouseleave', function () {
            d3.select(this).attr('opacity', 0.8 + Math.abs(val) * 0.2).attr('stroke', 'none');
            const tooltip = tooltipRef.current;
            if (tooltip) tooltip.style.display = 'none';
          });

        // Value text in cell (only if cell is large enough)
        if (cellSize > 30) {
          g.append('text')
            .attr('x', col * cellSize + cellSize / 2 - 0.5)
            .attr('y', row * cellSize + cellSize / 2)
            .attr('text-anchor', 'middle')
            .attr('dominant-baseline', 'middle')
            .attr('fill', '#fafafa')
            .attr('font-size', Math.min(10, cellSize * 0.28) + 'px')
            .attr('font-family', "'Geist Mono', monospace")
            .attr('pointer-events', 'none')
            .text(val.toFixed(2));
        }
      }
    }
  }, [symbols, matrix, width, height]);

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

  useEffect(() => {
    render();
  }, [render]);

  if (symbols.length === 0 || matrix.length === 0) {
    return (
      <Card className={cn('flex items-center justify-center p-4', className)} style={{ height }}>
        <p className="text-sm text-[var(--text-tertiary)]">No correlation data available</p>
      </Card>
    );
  }

  return (
    <div
      ref={containerRef}
      className={cn(
        'relative overflow-hidden rounded-lg border border-[var(--border-default)] bg-[var(--surface-0)]',
        className,
      )}
      style={{ height }}
      aria-label="Correlation matrix"
      role="img"
    >
      <svg ref={svgRef} width={width} height={height} />
      <div
        ref={tooltipRef}
        className="pointer-events-none absolute hidden rounded border border-[var(--border-default)] bg-[var(--surface-2)] px-2 py-1 text-xs text-[var(--text-primary)] shadow-lg"
        style={{ fontFamily: "'Geist Mono', monospace" }}
      />
    </div>
  );
}

function CorrelationMatrixSkeleton({ height = 400, className }: { height?: number; className?: string }) {
  return (
    <Card className={cn('p-4', className)} style={{ height }}>
      <div className="grid h-full grid-cols-6 grid-rows-6 gap-1">
        {Array.from({ length: 36 }).map((_, i) => (
          <Skeleton key={i} className="h-full w-full rounded-sm" />
        ))}
      </div>
    </Card>
  );
}

export { CorrelationMatrix, CorrelationMatrixSkeleton };
