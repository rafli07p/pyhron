import { useEffect, useRef } from 'react';
import { createChart, type IChartApi, ColorType } from 'lightweight-charts';
import { themeTokens } from '@/design_system/bloomberg_dark_theme_tokens';

interface SparklineChartProps {
  data: { time: string; value: number }[];
  width?: number;
  height?: number;
  color?: string;
  className?: string;
}

export default function SparklineChart({
  data,
  width = 120,
  height = 32,
  color,
  className = '',
}: SparklineChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  const lineColor =
    color ??
    (data.length >= 2 && data[data.length - 1].value >= data[0].value
      ? themeTokens.colors.semantic.positive
      : themeTokens.colors.semantic.negative);

  useEffect(() => {
    if (!containerRef.current || data.length === 0) return;

    const chart = createChart(containerRef.current, {
      width,
      height,
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: 'transparent',
      },
      grid: { vertLines: { visible: false }, horzLines: { visible: false } },
      crosshair: { mode: 0 },
      rightPriceScale: { visible: false },
      timeScale: { visible: false },
      handleScroll: false,
      handleScale: false,
    });

    const series = chart.addLineSeries({
      color: lineColor,
      lineWidth: 1,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false,
    });

    series.setData(data);
    chart.timeScale().fitContent();
    chartRef.current = chart;

    return () => {
      chart.remove();
      chartRef.current = null;
    };
  }, [data, width, height, lineColor]);

  if (data.length === 0) {
    return (
      <div
        className={`flex items-center justify-center text-bloomberg-text-muted text-xxs ${className}`}
        style={{ width, height }}
      >
        --
      </div>
    );
  }

  return <div ref={containerRef} className={className} />;
}
