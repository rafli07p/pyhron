'use client';

import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';
import { useTheme } from 'next-themes';

interface SectorWeight {
  name: string;
  value: number;
}

interface SectorPieChartProps {
  data?: SectorWeight[];
  height?: number;
}

const defaultData: SectorWeight[] = [
  { name: 'Financials', value: 35.2 },
  { name: 'Consumer', value: 18.5 },
  { name: 'Energy', value: 15.3 },
  { name: 'Materials', value: 12.8 },
  { name: 'Telecom', value: 8.4 },
  { name: 'Infrastructure', value: 5.6 },
  { name: 'Other', value: 4.2 },
];

const COLORS = ['#00d4aa', '#06b6d4', '#8b5cf6', '#f59e0b', '#ef4444', '#ec4899', '#64748b'];

export function SectorPieChart({ data = defaultData, height = 300 }: SectorPieChartProps) {
  const { resolvedTheme } = useTheme();
  const isDark = resolvedTheme === 'dark';

  return (
    <ResponsiveContainer width="100%" height={height}>
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          innerRadius={60}
          outerRadius={100}
          paddingAngle={2}
          dataKey="value"
          nameKey="name"
          label={({ name, value }) => `${name ?? ''} ${value}%`}
          labelLine={{ stroke: isDark ? '#475569' : '#94a3b8' }}
        >
          {data.map((_, index) => (
            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip
          contentStyle={{
            backgroundColor: isDark ? '#0f172a' : '#fff',
            border: `1px solid ${isDark ? '#1e293b' : '#e2e8f0'}`,
            borderRadius: '8px',
            fontSize: '12px',
          }}
          formatter={(value) => [`${Number(value).toFixed(1)}%`, 'Weight']}
        />
        <Legend
          wrapperStyle={{ fontSize: '12px', color: isDark ? '#94a3b8' : '#64748b' }}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}
