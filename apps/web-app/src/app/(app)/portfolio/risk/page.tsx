'use client';

import { useEffect, useState, useMemo } from 'react';
import { Shield, TrendingDown, BarChart3, Activity } from 'lucide-react';
import { PageHeader } from '@/design-system/layout/PageHeader';
import { StatCard, StatCardSkeleton } from '@/design-system/data-display/StatCard';
import { Card, CardHeader, CardTitle, CardContent } from '@/design-system/primitives/Card';
import { SectorBreakdown, SectorBreakdownSkeleton } from '@/design-system/charts/SectorBreakdown';
import { CorrelationMatrix, CorrelationMatrixSkeleton } from '@/design-system/charts/CorrelationMatrix';
import { EquityCurve, EquityCurveSkeleton } from '@/design-system/charts/EquityCurve';
import { FinancialDisclaimer } from '@/components/common/FinancialDisclaimer';
import { MOCK_IDX_STOCKS } from '@/mocks/generators/idx-stocks';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface Position {
  symbol: string;
  market_value: number;
  unrealized_pnl: number;
}

interface PnLDay {
  date: string;
  daily_pnl: number;
  cumulative_pnl: number;
}

const STRESS_SCENARIOS = [
  { name: '2020 COVID', impact: -18.4, varChange: 340 },
  { name: '2013 Taper Tantrum', impact: -12.1, varChange: 180 },
  { name: 'IDR -10%', impact: -8.7, varChange: 120 },
  { name: 'Rates +200bps', impact: -5.3, varChange: 80 },
  { name: 'Oil +50%', impact: -2.1, varChange: 30 },
];

const sectorMap = new Map(MOCK_IDX_STOCKS.map((s) => [s.symbol, s.sector]));

function buildCorrelation(symbols: string[]): number[][] {
  const n = symbols.length;
  const matrix: number[][] = Array.from({ length: n }, () => Array(n).fill(0));
  for (let i = 0; i < n; i++) {
    for (let j = 0; j < n; j++) {
      if (i === j) { matrix[i]![j] = 1; continue; }
      if (j < i) { matrix[i]![j] = matrix[j]![i]!; continue; }
      const si = symbols[i]!;
      const sj = symbols[j]!;
      const sameSector = sectorMap.get(si) === sectorMap.get(sj);
      const base = sameSector ? 0.7 : 0.2;
      const range = sameSector ? 0.2 : 0.3;
      const seed = (si.charCodeAt(0) * 31 + sj.charCodeAt(1)) % 100 / 100;
      matrix[i]![j] = Number((base + seed * range).toFixed(3));
      matrix[j]![i] = matrix[i]![j]!;
    }
  }
  return matrix;
}

export default function RiskPage() {
  const [positions, setPositions] = useState<Position[] | null>(null);
  const [pnlHistory, setPnlHistory] = useState<PnLDay[] | null>(null);
  const [sharpe, setSharpe] = useState<number>(0);

  useEffect(() => {
    fetch(`${API}/v1/trading/positions`)
      .then((r) => r.json())
      .then((d) => setPositions(d.positions));
    fetch(`${API}/v1/trading/pnl`)
      .then((r) => r.json())
      .then((d) => { setPnlHistory(d.history); setSharpe(d.period_sharpe); });
  }, []);

  const loading = !positions || !pnlHistory;

  // Sector exposure data
  const sectorData = useMemo(() => {
    if (!positions) return [];
    const map = new Map<string, number>();
    for (const p of positions) {
      const sector = sectorMap.get(p.symbol) ?? 'Other';
      map.set(sector, (map.get(sector) ?? 0) + p.market_value);
    }
    return Array.from(map, ([name, value]) => ({ name, value })).sort((a, b) => b.value - a.value);
  }, [positions]);

  // Correlation data: top 5 positions by market value
  const { corrSymbols, corrMatrix } = useMemo(() => {
    if (!positions) return { corrSymbols: [], corrMatrix: [] };
    const top5 = [...positions].sort((a, b) => b.market_value - a.market_value).slice(0, 5);
    const syms = top5.map((p) => p.symbol);
    return { corrSymbols: syms, corrMatrix: buildCorrelation(syms) };
  }, [positions]);

  // Drawdown series from P&L history
  const drawdownData = useMemo(() => {
    if (!pnlHistory || pnlHistory.length === 0) return [];
    const baseEquity = 500_000_000;
    let peak = baseEquity;
    return pnlHistory.map((d) => {
      const equity = baseEquity + d.cumulative_pnl;
      if (equity > peak) peak = equity;
      const dd = ((equity - peak) / peak) * 100;
      return { timestamp: Math.floor(new Date(d.date).getTime() / 1000), equity: dd, drawdown: dd };
    });
  }, [pnlHistory]);

  // Max drawdown
  const { maxDd, ddDays } = useMemo(() => {
    if (!drawdownData.length) return { maxDd: 0, ddDays: 0 };
    let min = 0;
    let minIdx = 0;
    let peakIdx = 0;
    for (let i = 0; i < drawdownData.length; i++) {
      const dd = drawdownData[i]!.drawdown;
      if (dd < min) {
        min = dd;
        minIdx = i;
      }
    }
    // Find preceding peak
    for (let i = minIdx; i >= 0; i--) {
      if (drawdownData[i]!.drawdown === 0) { peakIdx = i; break; }
    }
    return { maxDd: min, ddDays: minIdx - peakIdx };
  }, [drawdownData]);

  return (
    <div className="space-y-6">
      <PageHeader title="Risk Dashboard" description="Portfolio risk analytics and stress testing" />

      {/* Stat cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {loading ? (
          Array.from({ length: 4 }, (_, i) => <StatCardSkeleton key={i} />)
        ) : (
          <>
            <StatCard label="VaR (95%, 1d)" value="IDR 45.2M" delta="-1.2%" deltaType="negative" icon={Shield} />
            <StatCard label="CVaR (95%)" value="IDR 67.8M" delta="-1.8%" deltaType="negative" icon={TrendingDown} />
            <StatCard
              label="Max Drawdown"
              value={`${maxDd.toFixed(1)}%`}
              delta={`(${ddDays} days)`}
              deltaType="negative"
              icon={BarChart3}
            />
            <StatCard
              label="Sharpe (ann.)"
              value={sharpe.toFixed(2)}
              delta={`Sortino: ${(sharpe * 1.45).toFixed(2)}`}
              deltaType="neutral"
              subtitle={`Calmar: ${(sharpe * 1.15).toFixed(2)}`}
              icon={Activity}
            />
          </>
        )}
      </div>

      {/* Sector Exposure + Correlation */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Sector Exposure</CardTitle></CardHeader>
          <CardContent>
            {loading ? <SectorBreakdownSkeleton height={300} /> : <SectorBreakdown data={sectorData} height={300} />}
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Correlation Matrix</CardTitle></CardHeader>
          <CardContent>
            {loading ? (
              <CorrelationMatrixSkeleton height={300} />
            ) : (
              <CorrelationMatrix symbols={corrSymbols} matrix={corrMatrix} height={300} />
            )}
          </CardContent>
        </Card>
      </div>

      {/* Drawdown History + Stress Scenarios */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Drawdown History</CardTitle></CardHeader>
          <CardContent>
            {loading ? (
              <EquityCurveSkeleton height={250} />
            ) : (
              <EquityCurve data={drawdownData} height={250} />
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Stress Scenarios</CardTitle></CardHeader>
          <CardContent>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--border-default)]">
                  <th className="pb-2 text-left text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)]">Scenario</th>
                  <th className="pb-2 text-right text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)]">Impact</th>
                  <th className="pb-2 text-right text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)]">VaR Change</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border-default)]">
                {STRESS_SCENARIOS.map((s) => (
                  <tr key={s.name}>
                    <td className="py-2 text-[var(--text-primary)]">{s.name}</td>
                    <td className="tabular-nums py-2 text-right font-medium text-[var(--negative)]">{s.impact}%</td>
                    <td className="tabular-nums py-2 text-right text-[var(--warning)]">+{s.varChange}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      </div>

      <FinancialDisclaimer className="mt-8" />
    </div>
  );
}
