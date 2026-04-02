'use client';

import { PageHeader } from '@/design-system/layout/PageHeader';
import { Card } from '@/design-system/primitives/Card';
import { Badge } from '@/design-system/primitives/Badge';
import { TierGate } from '@/components/common/TierGate';
import { useTierGate } from '@/hooks/useTierGate';
import { Brain, FlaskConical, Server, Zap } from 'lucide-react';
import Link from 'next/link';

const sections = [
  {
    href: '/ml/experiments',
    icon: FlaskConical,
    title: 'Experiments',
    description: 'MLflow experiment browser and comparison',
    stat: '24',
    statLabel: 'Total experiments',
  },
  {
    href: '/ml/models',
    icon: Brain,
    title: 'Model Registry',
    description: 'Deployed, staging, and archived models',
    stat: '8',
    statLabel: 'Registered models',
  },
  {
    href: '/ml/training',
    icon: Server,
    title: 'Training Jobs',
    description: 'Launch and monitor training jobs',
    stat: '2',
    statLabel: 'Running jobs',
  },
];

export default function MLPage() {
  const { hasAccess } = useTierGate('ml.experiments');

  if (!hasAccess) {
    return (
      <div className="space-y-6">
        <PageHeader title="ML Pipeline" description="Machine learning model management" />
        <TierGate requiredTier="strategist" featureName="ML Pipeline" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader title="ML Pipeline" description="Machine learning experiments, models, and training" />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {sections.map((section) => {
          const Icon = section.icon;
          return (
            <Link key={section.href} href={section.href}>
              <Card className="p-6 transition-colors hover:border-[var(--accent-500)]">
                <div className="flex items-center gap-2">
                  <Icon className="h-4 w-4 text-[var(--accent-500)]" />
                  <h3 className="text-sm font-semibold text-[var(--text-primary)]">{section.title}</h3>
                </div>
                <p className="mt-1 text-xs text-[var(--text-tertiary)]">{section.description}</p>
                <p className="mt-3 text-2xl font-bold tabular-nums text-[var(--accent-500)]">{section.stat}</p>
                <p className="text-xs text-[var(--text-tertiary)]">{section.statLabel}</p>
              </Card>
            </Link>
          );
        })}
      </div>

      <Card className="p-6">
        <h3 className="text-sm font-semibold text-[var(--text-primary)]">Recent Models</h3>
        <div className="mt-4 space-y-3">
          {[
            { name: 'MomentumV3', version: '3.2.1', sharpe: 1.84, status: 'deployed' },
            { name: 'EnsembleV2', version: '2.1.0', sharpe: 1.62, status: 'deployed' },
            { name: 'MeanRevV1', version: '1.5.3', sharpe: 1.45, status: 'staging' },
            { name: 'FactorAlphaV1', version: '1.0.0', sharpe: 1.28, status: 'archived' },
          ].map((model) => (
            <div key={model.name} className="flex items-center justify-between rounded-md px-2 py-2 hover:bg-[var(--surface-3)]">
              <div className="flex items-center gap-3">
                <Zap className="h-4 w-4 text-[var(--accent-500)]" />
                <div>
                  <span className="text-sm font-medium text-[var(--text-primary)]">{model.name}</span>
                  <span className="ml-2 text-xs text-[var(--text-tertiary)]">v{model.version}</span>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-xs tabular-nums text-[var(--text-secondary)]">
                  Sharpe: {model.sharpe.toFixed(2)}
                </span>
                <Badge variant={model.status === 'deployed' ? 'positive' : model.status === 'staging' ? 'warning' : 'default'}>
                  {model.status}
                </Badge>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
