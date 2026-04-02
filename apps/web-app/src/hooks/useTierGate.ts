'use client';

import { useSession } from 'next-auth/react';
import {
  FEATURE_TIERS,
  TIER_HIERARCHY,
  type FeatureKey,
  type Tier,
} from '@/constants/tiers';

export function useTierGate(feature: FeatureKey) {
  const { data: session } = useSession();
  const userTier = ((session?.user as Record<string, unknown>)?.tier as Tier) ?? 'explorer';
  const requiredTier = FEATURE_TIERS[feature];

  const hasAccess = TIER_HIERARCHY[userTier] >= TIER_HIERARCHY[requiredTier];

  return { hasAccess, userTier, requiredTier };
}

export function useTier(): Tier {
  const { data: session } = useSession();
  return ((session?.user as Record<string, unknown>)?.tier as Tier) ?? 'explorer';
}
