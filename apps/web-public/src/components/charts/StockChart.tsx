'use client';

import { useEffect, useRef, useState } from 'react';
import { createChart, AreaSeries, type IChartApi, type ISeriesApi, ColorType } from 'lightweight-charts';
import { useTheme } from 'next-themes';

interface ChartDataPoint {
  time: string;
  value: number;
}

interface StockChartProps {
  data: ChartDataPoint[];
  height?: number;
}

const RANGES = ['1M', '3M', '6M', 'YTD', '1Y', '3Y', '5Y', 'MAX'] as const;

function filterByRange(data: ChartDataPoint[], range: string): ChartDataPoint[] {
  if (range === 'MAX') return data;
  const now = new Date();
  let cutoff: Date;
  switch (range) {
    case '1M': cutoff = new Date(now.setMonth(now.getMonth() - 1)); break;
    case '3M': cutoff = new Date(now.setMonth(now.getMonth() - 3)); break;
    case '6M': cutoff = new Date(now.setMonth(now.getMonth() - 6)); break;
    case 'YTD': cutoff = new Date(now.getFullYear(), 0, 1); break;
    case '1Y': cutoff = new Date(now.setFullYear(now.getFullYear() - 1)); break;
    case '3Y': cutoff = new Date(now.setFullYear(now.getFullYear() - 3)); break;
    case '5Y': cutoff = new Date(now.setFullYear(now.getFullYear() - 5)); break;
    default: return data;
  }
  const cutoffStr = cutoff.toISOString().split('T')[0];
  return data.filter((d) => d.time >= cutoffStr);
}

export function StockChart({ data, height = 400 }: StockChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Area'> | null>(null);
  const { resolvedTheme } = useTheme();
  const [activeRange, setActiveRange] = useState<string>('1Y');

  useEffect(() => {
    if (!containerRef.current) return;
    const isDark = resolvedTheme === 'dark';

    const chart = createChart(containerRef.current, {
      height,
      layout: {
        background: { type: ColorType.Solid, color: isDark ? '#0a0e1a' : '#ffffff' },
        textColor: isDark ? '#94a3b8' : '#475569',
        fontFamily: 'Satoshi, sans-serif',
      },
      grid: {
        vertLines: { color: isDark ? '#1e293b' : '#f1f5f9' },
        horzLines: { color: isDark ? '#1e293b' : '#f1f5f9' },
      },
      crosshair: { mode: 0 },
      rightPriceScale: { borderColor: isDark ? '#1e293b' : '#e2e8f0' },
      timeScale: { borderColor: isDark ? '#1e293b' : '#e2e8f0' },
    });

    const series = chart.addSeries(AreaSeries, {
      lineColor: '#00d4aa',
      topColor: 'rgba(0,212,170,0.3)',
      bottomColor: 'rgba(0,212,170,0.05)',
      lineWidth: 2,
    });

    chartRef.current = chart;
    seriesRef.current = series;

    const filtered = filterByRange(data, activeRange);
    series.setData(filtered);
    chart.timeScale().fitContent();

    const handleResize = () => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [resolvedTheme, height]);

  useEffect(() => {
    if (!seriesRef.current || !chartRef.current) return;
    const filtered = filterByRange(data, activeRange);
    seriesRef.current.setData(filtered);
    chartRef.current.timeScale().fitContent();
  }, [data, activeRange]);

  return (
    <div>
      <div className="mb-4 flex flex-wrap gap-1">
        {RANGES.map((r) => (
          <button
            key={r}
            onClick={() => setActiveRange(r)}
            className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
              activeRange === r
                ? 'bg-accent-500 text-primary-900'
                : 'text-text-secondary hover:bg-bg-tertiary'
            }`}
          >
            {r}
          </button>
        ))}
      </div>
      <div ref={containerRef} className="w-full rounded-lg border border-border overflow-hidden" />
    </div>
  );
}
