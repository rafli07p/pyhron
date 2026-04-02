'use client';

import { PageHeader } from '@/design-system/layout/PageHeader';
import { Card, CardContent } from '@/design-system/primitives/Card';
import { TierGate } from '@/components/common/TierGate';
import { useTierGate } from '@/hooks/useTierGate';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

const MOCK_SIGNALS = [
  { symbol: 'BMRI', name: 'Bank Mandiri', direction: 'buy' as const, confidence: 0.87, expectedReturn: 4.2, model: 'MomentumV3', horizon: '5d', generatedAt: '2025-03-15T09:30:00' },
  { symbol: 'ASII', name: 'Astra International', direction: 'hold' as const, confidence: 0.62, expectedReturn: 0.8, model: 'EnsembleV2', horizon: '5d', generatedAt: '2025-03-15T09:30:00' },
  { symbol: 'UNVR', name: 'Unilever Indonesia', direction: 'sell' as const, confidence: 0.91, expectedReturn: -3.1, model: 'MeanRevV1', horizon: '5d', generatedAt: '2025-03-15T09:30:00' },
  { symbol: 'TLKM', name: 'Telkom Indonesia', direction: 'buy' as const, confidence: 0.74, expectedReturn: 2.8, model: 'MomentumV3', horizon: '5d', generatedAt: '2025-03-15T09:30:00' },
  { symbol: 'BBCA', name: 'Bank Central Asia', direction: 'hold' as const, confidence: 0.55, expectedReturn: 0.3, model: 'EnsembleV2', horizon: '5d', generatedAt: '2025-03-15T09:30:00' },
  { symbol: 'BBRI', name: 'Bank Rakyat Indonesia', direction: 'buy' as const, confidence: 0.81, expectedReturn: 3.5, model: 'MomentumV3', horizon: '5d', generatedAt: '2025-03-15T09:30:00' },
];

const directionConfig = {
  buy: { icon: TrendingUp, color: 'text-[var(--positive)]', bg: 'bg-[var(--positive-muted)]', label: 'Buy' },
  sell: { icon: TrendingDown, color: 'text-[var(--negative)]', bg: 'bg-[var(--negative-muted)]', label: 'Sell' },
  hold: { icon: Minus, color: 'text-[var(--warning)]', bg: 'bg-[var(--warning-muted)]', label: 'Hold' },
};

export default function SignalsPage() {
  const { hasAccess } = useTierGate('research.signals');

  if (!hasAccess) {
    return (
      <div className="space-y-6">
        <PageHeader title="Signal Dashboard" description="ML-generated trading signals" />
        <TierGate requiredTier="strategist" featureName="ML Signals" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Signal Dashboard" description="ML-generated trading signals with confidence scores" />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {MOCK_SIGNALS.map((signal) => {
          const config = directionConfig[signal.direction];
          const Icon = config.icon;
          return (
            <Card key={signal.symbol} className="p-4">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-[var(--text-primary)]">{signal.symbol}</span>
                    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${config.bg} ${config.color}`}>
                      <Icon className="h-3 w-3" />
                      {config.label}
                    </span>
                  </div>
                  <p className="text-xs text-[var(--text-tertiary)]">{signal.name}</p>
                </div>
                <div className="text-right">
                  <p className="text-lg font-bold tabular-nums text-[var(--text-primary)]">
                    {(signal.confidence * 100).toFixed(0)}%
                  </p>
                  <p className="text-[10px] text-[var(--text-tertiary)]">confidence</p>
                </div>
              </div>
              {/* Confidence bar */}
              <div className="mt-3 h-1.5 w-full rounded-full bg-[var(--surface-3)]">
                <div
                  className="h-full rounded-full bg-[var(--accent-500)]"
                  style={{ width: `${signal.confidence * 100}%` }}
                />
              </div>
              <CardContent className="mt-3 flex items-center justify-between p-0 text-xs text-[var(--text-tertiary)]">
                <span>Expected: {signal.expectedReturn > 0 ? '+' : ''}{signal.expectedReturn}%</span>
                <span>{signal.model}</span>
                <span>{signal.horizon}</span>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
