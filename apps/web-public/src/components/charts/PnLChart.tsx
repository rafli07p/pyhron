'use client';

import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { useTheme } from 'next-themes';

interface PnLDataPoint {
  date: string;
  value: number;
}

interface PnLChartProps {
  data?: PnLDataPoint[];
  height?: number;
}

const sampleData: PnLDataPoint[] = Array.from({ length: 90 }, (_, i) => {
  const date = new Date(2026, 0, 1);
  date.setDate(date.getDate() + i);
  return {
    date: date.toISOString().split('T')[0],
    value: Math.round((100 + i * 0.3 + Math.sin(i / 5) * 3 + (Math.random() - 0.4) * 2) * 100) / 100,
  };
});

export function PnLChart({ data = sampleData, height = 300 }: PnLChartProps) {
  const { resolvedTheme } = useTheme();
  const isDark = resolvedTheme === 'dark';

  const minVal = Math.min(...data.map((d) => d.value));
  const maxVal = Math.max(...data.map((d) => d.value));

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
        <defs>
          <linearGradient id="pnlGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#00d4aa" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#00d4aa" stopOpacity={0.05} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke={isDark ? '#1e293b' : '#f1f5f9'} />
        <XAxis
          dataKey="date"
          tick={{ fontSize: 11, fill: isDark ? '#94a3b8' : '#64748b' }}
          tickFormatter={(v: string) => v.slice(5)}
          interval="preserveStartEnd"
          stroke={isDark ? '#1e293b' : '#e2e8f0'}
        />
        <YAxis
          domain={[Math.floor(minVal - 1), Math.ceil(maxVal + 1)]}
          tick={{ fontSize: 11, fill: isDark ? '#94a3b8' : '#64748b' }}
          tickFormatter={(v: number) => `${v.toFixed(0)}%`}
          stroke={isDark ? '#1e293b' : '#e2e8f0'}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: isDark ? '#0f172a' : '#fff',
            border: `1px solid ${isDark ? '#1e293b' : '#e2e8f0'}`,
            borderRadius: '8px',
            fontSize: '12px',
          }}
          formatter={(value) => [`${Number(value).toFixed(2)}%`, 'Return']}
        />
        <Area type="monotone" dataKey="value" stroke="#00d4aa" strokeWidth={2} fill="url(#pnlGrad)" />
      </AreaChart>
    </ResponsiveContainer>
  );
}
