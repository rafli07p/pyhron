'use client';

import { type ReactNode } from 'react';
import { Lock, ArrowRight } from 'lucide-react';
import Link from 'next/link';
import { TIERS, type Tier } from '@/constants/tiers';
import { useTier } from '@/hooks/useTierGate';
import { Button } from '@/design-system/primitives/Button';
import { Card, CardContent } from '@/design-system/primitives/Card';

interface TierGateProps {
  requiredTier: Tier;
  featureName?: string;
  children?: ReactNode;
  fallback?: ReactNode;
}

export function TierGate({
  requiredTier,
  featureName,
  children,
  fallback,
}: TierGateProps) {
  const userTier = useTier();
  const tierConfig = TIERS[requiredTier];

  const tierOrder: Tier[] = ['explorer', 'strategist', 'operator'];
  const hasAccess =
    tierOrder.indexOf(userTier) >= tierOrder.indexOf(requiredTier);

  if (hasAccess) {
    return <>{children}</>;
  }

  if (fallback) {
    return <>{fallback}</>;
  }

  const isOperator = requiredTier === 'operator';

  return (
    <Card className="border-border mx-auto max-w-lg border-dashed">
      <CardContent className="flex flex-col items-center p-8 text-center">
        <div
          className="bg-surface-2 mb-4 flex h-12 w-12 items-center justify-center rounded-full"
          aria-hidden="true"
        >
          <Lock className="text-text-tertiary h-5 w-5" />
        </div>
        <h3 className="text-text-primary mb-2 text-lg font-semibold">
          Upgrade to {tierConfig.label}
        </h3>
        <p className="text-text-secondary mb-6 text-sm">
          {featureName
            ? `${featureName} requires the ${tierConfig.label} plan.`
            : `This feature requires the ${tierConfig.label} plan.`}{' '}
          {tierConfig.description}
        </p>
        <Link href={isOperator ? '/contact' : '/pricing'}>
          <Button variant="primary" size="sm">
            {isOperator ? 'Request Access' : 'View Plans'}
            <ArrowRight className="ml-1.5 h-4 w-4" />
          </Button>
        </Link>
      </CardContent>
    </Card>
  );
}

export function TierBadge({ tier }: { tier: Tier }) {
  const config = TIERS[tier];
  return (
    <span
      className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium"
      style={{ color: config.color, backgroundColor: `color-mix(in srgb, ${config.color} 15%, transparent)` }}
    >
      {config.label}
    </span>
  );
}
