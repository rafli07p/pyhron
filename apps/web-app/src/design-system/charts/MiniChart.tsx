'use client';

import { useRef, useEffect } from 'react';
import { cn } from '@/lib/utils';

interface MiniChartProps {
  data: number[];
  width?: number;
  height?: number;
  positive?: boolean;
  className?: string;
}

function MiniChart({ data, width = 120, height = 32, positive = true, className }: MiniChartProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || data.length < 2) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    ctx.scale(dpr, dpr);

    ctx.clearRect(0, 0, width, height);

    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min || 1;
    const padding = 1;

    const stepX = (width - padding * 2) / (data.length - 1);

    const getX = (i: number) => padding + i * stepX;
    const getY = (v: number) => height - padding - ((v - min) / range) * (height - padding * 2);

    const lineColor = positive ? '#22c55e' : '#ef4444';
    const fillColor = positive ? 'rgba(34,197,94,0.15)' : 'rgba(239,68,68,0.15)';

    // Fill area below line
    ctx.beginPath();
    ctx.moveTo(getX(0), height);
    for (let i = 0; i < data.length; i++) {
      ctx.lineTo(getX(i), getY(data[i]!));
    }
    ctx.lineTo(getX(data.length - 1), height);
    ctx.closePath();
    ctx.fillStyle = fillColor;
    ctx.fill();

    // Draw line
    ctx.beginPath();
    ctx.moveTo(getX(0), getY(data[0]!));
    for (let i = 1; i < data.length; i++) {
      ctx.lineTo(getX(i), getY(data[i]!));
    }
    ctx.strokeStyle = lineColor;
    ctx.lineWidth = 1.5;
    ctx.lineJoin = 'round';
    ctx.lineCap = 'round';
    ctx.stroke();
  }, [data, width, height, positive]);

  if (data.length < 2) {
    return (
      <div
        className={cn('inline-block', className)}
        style={{ width, height }}
        aria-label="Sparkline chart — insufficient data"
      />
    );
  }

  return (
    <canvas
      ref={canvasRef}
      className={cn('inline-block', className)}
      style={{ width, height }}
      aria-label={`Sparkline chart — ${positive ? 'positive' : 'negative'} trend`}
      role="img"
    />
  );
}

export { MiniChart };
