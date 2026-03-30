'use client';

import { SectorPieChart } from '@/components/charts/SectorPieChart';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { useTheme } from 'next-themes';

const factorData = [
  { factor: 'Value', exposure: 0.32 },
  { factor: 'Momentum', exposure: 0.48 },
  { factor: 'Quality', exposure: 0.21 },
  { factor: 'Size', exposure: -0.15 },
  { factor: 'Low Vol', exposure: 0.18 },
];

export function PortfolioCharts() {
  const { resolvedTheme } = useTheme();
  const isDark = resolvedTheme === 'dark';

  return (
    <>
      <div className="rounded-lg border border-border bg-bg-secondary p-6">
        <h3 className="text-sm font-medium text-text-muted mb-4">Factor Exposure</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={factorData} layout="vertical" margin={{ left: 20, right: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={isDark ? '#1e293b' : '#f1f5f9'} />
            <XAxis
              type="number"
              tick={{ fontSize: 11, fill: isDark ? '#94a3b8' : '#64748b' }}
              stroke={isDark ? '#1e293b' : '#e2e8f0'}
            />
            <YAxis
              dataKey="factor"
              type="category"
              tick={{ fontSize: 12, fill: isDark ? '#94a3b8' : '#64748b' }}
              stroke={isDark ? '#1e293b' : '#e2e8f0'}
              width={80}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: isDark ? '#0f172a' : '#fff',
                border: `1px solid ${isDark ? '#1e293b' : '#e2e8f0'}`,
                borderRadius: '8px',
                fontSize: '12px',
              }}
              formatter={(value) => [Number(value).toFixed(2), 'Exposure']}
            />
            <Bar dataKey="exposure" fill="#00d4aa" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="rounded-lg border border-border bg-bg-secondary p-6">
        <h3 className="text-sm font-medium text-text-muted mb-4">Sector Allocation</h3>
        <SectorPieChart />
      </div>
    </>
  );
}
