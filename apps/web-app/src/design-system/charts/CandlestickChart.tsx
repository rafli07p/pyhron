'use client';

import { useRef, useEffect, useCallback } from 'react';
import { createChart, type IChartApi, type ISeriesApi, CrosshairMode, CandlestickSeries, HistogramSeries } from 'lightweight-charts';
import { cn } from '@/lib/utils';
import { Card } from '@/design-system/primitives/Card';
import { Skeleton } from '@/design-system/primitives/Skeleton';

export interface OHLCV {
  timestamp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface CandlestickChartProps {
  data: OHLCV[];
  volume?: boolean;
  height?: number;
  timeframe?: string;
  className?: string;
}

function CandlestickChart({
  data,
  volume = true,
  height = 400,
  timeframe = '1D',
  className,
}: CandlestickChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null);

  const initChart = useCallback(() => {
    const container = containerRef.current;
    if (!container) return;

    // Clean up existing chart
    if (chartRef.current) {
      chartRef.current.remove();
      chartRef.current = null;
    }

    const chart = createChart(container, {
      width: container.clientWidth,
      height,
      layout: {
        background: { color: '#09090b' },
        textColor: '#a1a1aa',
        fontFamily: 'var(--font-sans), system-ui, -apple-system, sans-serif',
      },
      grid: {
        vertLines: { color: 'rgba(255,255,255,0.06)' },
        horzLines: { color: 'rgba(255,255,255,0.06)' },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: {
          color: 'rgba(255,255,255,0.2)',
          labelBackgroundColor: '#27272a',
        },
        horzLine: {
          color: 'rgba(255,255,255,0.2)',
          labelBackgroundColor: '#27272a',
        },
      },
      rightPriceScale: {
        borderColor: 'rgba(255,255,255,0.06)',
      },
      timeScale: {
        borderColor: 'rgba(255,255,255,0.06)',
        timeVisible: true,
        secondsVisible: false,
      },
    });

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#22c55e',
      downColor: '#ef4444',
      borderUpColor: '#22c55e',
      borderDownColor: '#ef4444',
      wickUpColor: '#22c55e',
      wickDownColor: '#ef4444',
    });

    candleSeriesRef.current = candleSeries;

    if (volume) {
      const volumeSeries = chart.addSeries(HistogramSeries, {
        priceFormat: { type: 'volume' },
        priceScaleId: 'volume',
      });

      chart.priceScale('volume').applyOptions({
        scaleMargins: { top: 0.8, bottom: 0 },
      });

      volumeSeriesRef.current = volumeSeries;
    }

    chartRef.current = chart;
  }, [height, volume]);

  // Create chart on mount
  useEffect(() => {
    initChart();

    return () => {
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
      }
    };
  }, [initChart]);

  // Update data when it changes
  useEffect(() => {
    if (!chartRef.current || data.length === 0) return;

    const candles = data.map((d) => ({
      time: d.timestamp as import('lightweight-charts').Time,
      open: d.open,
      high: d.high,
      low: d.low,
      close: d.close,
    }));

    candleSeriesRef.current?.setData(candles);

    if (volume && volumeSeriesRef.current) {
      const volumes = data.map((d) => ({
        time: d.timestamp as import('lightweight-charts').Time,
        value: d.volume,
        color: d.close >= d.open ? 'rgba(34,197,94,0.3)' : 'rgba(239,68,68,0.3)',
      }));
      volumeSeriesRef.current.setData(volumes);
    }

    chartRef.current.timeScale().fitContent();
  }, [data, volume]);

  // Resize observer
  useEffect(() => {
    const container = containerRef.current;
    if (!container || !chartRef.current) return;

    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry && chartRef.current) {
        chartRef.current.applyOptions({ width: entry.contentRect.width });
      }
    });

    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  if (data.length === 0) {
    return (
      <Card className={cn('flex items-center justify-center p-4', className)} style={{ height }}>
        <p className="text-sm text-[var(--text-tertiary)]">No chart data available</p>
      </Card>
    );
  }

  return (
    <div
      ref={containerRef}
      className={cn('overflow-hidden rounded-lg border border-[var(--border-default)]', className)}
      style={{ height }}
      aria-label={`Candlestick chart — ${timeframe} timeframe`}
      role="img"
    />
  );
}

const SKELETON_BAR_HEIGHTS = [
  71, 43, 55, 28, 67, 38, 74, 51, 33, 62,
  46, 79, 25, 58, 41, 69, 35, 53, 76, 30,
  64, 48, 22, 57, 39, 72, 44, 60, 27, 68,
  50, 36, 75, 42, 66, 31, 54, 47, 73, 29,
];

function CandlestickChartSkeleton({ height = 400, className }: { height?: number; className?: string }) {
  return (
    <Card className={cn('p-4', className)} style={{ height }}>
      <div className="flex h-full flex-col justify-between">
        <div className="flex items-center justify-between">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-4 w-16" />
        </div>
        <div className="flex flex-1 items-end gap-1 px-2 pt-4">
          {SKELETON_BAR_HEIGHTS.map((h, i) => (
            <Skeleton
              key={i}
              className="flex-1"
              style={{ height: `${h}%` }}
            />
          ))}
        </div>
        <Skeleton className="mt-2 h-3 w-full" />
      </div>
    </Card>
  );
}

export { CandlestickChart, CandlestickChartSkeleton };
