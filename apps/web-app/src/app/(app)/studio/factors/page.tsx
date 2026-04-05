'use client';

import { PageHeader } from '@/design-system/layout/PageHeader';
import { Card, CardHeader, CardTitle, CardContent } from '@/design-system/primitives/Card';
import { Badge } from '@/design-system/primitives/Badge';
import { TierGate } from '@/components/common/TierGate';
import { useTierGate } from '@/hooks/useTierGate';
import { TrendingUp, Scale, Award, Ruler } from 'lucide-react';

const factors = [
  {
    name: 'Momentum',
    icon: TrendingUp,
    description: 'Stocks with strong recent price performance tend to continue outperforming over short to medium horizons.',
    score: 0.72,
    loading: 0.84,
    topHoldings: ['BBRI', 'BBCA', 'BMRI'],
    returnYtd: '+14.2%',
  },
  {
    name: 'Value',
    icon: Scale,
    description: 'Stocks trading at low valuations relative to fundamentals such as earnings, book value, or cash flow.',
    score: 0.58,
    loading: 0.61,
    topHoldings: ['ASII', 'BBNI', 'INDF'],
    returnYtd: '+8.7%',
  },
  {
    name: 'Quality',
    icon: Award,
    description: 'Companies with high profitability, stable earnings, and strong balance sheets.',
    score: 0.81,
    loading: 0.76,
    topHoldings: ['BBCA', 'UNVR', 'TLKM'],
    returnYtd: '+11.3%',
  },
  {
    name: 'Size',
    icon: Ruler,
    description: 'Small-cap stocks historically earn higher risk-adjusted returns than large-cap stocks.',
    score: 0.44,
    loading: 0.39,
    topHoldings: ['MDKA', 'ACES', 'MAPI'],
    returnYtd: '+3.1%',
  },
];

function ScoreBar({ value, label }: { value: number; label: string }) {
  const color = value >= 0.7 ? 'var(--positive)' : value >= 0.5 ? 'var(--warning)' : 'var(--negative)';
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-xs">
        <span className="text-[var(--text-tertiary)]">{label}</span>
        <span className="tabular-nums text-[var(--text-secondary)]">{(value * 100).toFixed(0)}%</span>
      </div>
      <div className="h-1.5 w-full rounded-full bg-[var(--surface-3)]">
        <div
          className="h-1.5 rounded-full transition-all"
          style={{ width: `${value * 100}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
}

export default function FactorsPage() {
  const { hasAccess } = useTierGate('studio.factors');

  if (!hasAccess) {
    return (
      <div className="space-y-3">
        <PageHeader title="Factor Analysis" description="Explore systematic risk factors in the IDX market" />
        <TierGate requiredTier="strategist" featureName="Factor Analysis" />
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <PageHeader
        title="Factor Analysis"
        description="Explore systematic risk factors in the IDX market"
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {factors.map((factor) => {
          const Icon = factor.icon;
          return (
            <Card key={factor.name}>
              <CardHeader>
                <div className="flex items-start justify-between">
                  <CardTitle className="flex items-center gap-2">
                    <div className="rounded-md bg-[var(--accent-50)] p-1.5">
                      <Icon className="h-4 w-4 text-[var(--accent-500)]" />
                    </div>
                    {factor.name}
                  </CardTitle>
                  <Badge variant={factor.returnYtd.startsWith('+') ? 'positive' : 'negative'}>
                    YTD {factor.returnYtd}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <p className="mb-4 text-xs text-[var(--text-secondary)]">{factor.description}</p>

                <div className="space-y-3">
                  <ScoreBar value={factor.score} label="Factor Score" />
                  <ScoreBar value={factor.loading} label="Factor Loading" />
                </div>

                <div className="mt-4">
                  <p className="mb-1.5 text-[10px] font-medium uppercase tracking-wider text-[var(--text-tertiary)]">
                    Top Holdings
                  </p>
                  <div className="flex gap-1.5">
                    {factor.topHoldings.map((h) => (
                      <span
                        key={h}
                        className="rounded bg-[var(--surface-3)] px-2 py-0.5 text-xs font-medium text-[var(--text-secondary)]"
                      >
                        {h}
                      </span>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
