export type Tier = 'explorer' | 'strategist' | 'operator';

interface TierConfig {
  name: string;
  label: string;
  labelId: string;
  description: string;
  descriptionId: string;
  color: string;
  pricing: 'free' | 'self-serve' | 'contact';
}

export const TIERS: Record<Tier, TierConfig> = {
  explorer: {
    name: 'explorer',
    label: 'Explorer',
    labelId: 'Explorer',
    description: 'Watch & Learn — market observation and discovery',
    descriptionId: 'Pantau & Pelajari — observasi dan penemuan pasar',
    color: 'var(--text-tertiary)',
    pricing: 'free',
  },
  strategist: {
    name: 'strategist',
    label: 'Strategist',
    labelId: 'Strategist',
    description: 'Build & Test — full analytics suite with paper trading',
    descriptionId: 'Bangun & Uji — suite analitik lengkap dengan paper trading',
    color: 'var(--accent-500)',
    pricing: 'self-serve',
  },
  operator: {
    name: 'operator',
    label: 'Operator',
    labelId: 'Operator',
    description: 'Deploy & Execute — live algorithmic trading with guardrails',
    descriptionId: 'Deploy & Eksekusi — trading algoritmik live dengan guardrails',
    color: 'var(--warning)',
    pricing: 'contact',
  },
} as const;

export const TIER_HIERARCHY: Record<Tier, number> = {
  explorer: 0,
  strategist: 1,
  operator: 2,
};

export const FEATURE_TIERS = {
  // Markets
  'markets.realtime': 'strategist',
  'markets.delayed': 'explorer',
  'markets.screener.basic': 'explorer',
  'markets.screener.full': 'strategist',
  'markets.watchlists.multi': 'strategist',

  // Studio
  'studio.workbench.read': 'explorer',
  'studio.workbench.create': 'strategist',
  'studio.dashboards.preset': 'explorer',
  'studio.dashboards.custom': 'strategist',
  'studio.backtests': 'strategist',
  'studio.factors': 'strategist',

  // Research
  'research.articles.preview': 'explorer',
  'research.articles.full': 'strategist',
  'research.signals': 'strategist',

  // Portfolio & Risk
  'portfolio.positions': 'strategist',
  'portfolio.orders': 'strategist',
  'portfolio.risk': 'strategist',
  'portfolio.performance': 'strategist',

  // Execution
  'execution.paper': 'strategist',
  'execution.live': 'operator',
  'execution.algorithms': 'operator',
  'execution.guardrails': 'operator',
  'execution.killswitch': 'operator',

  // Data
  'data.catalog.browse': 'explorer',
  'data.catalog.chart': 'strategist',
  'data.api': 'strategist',
  'data.api.unlimited': 'operator',
  'data.explorer': 'strategist',
  'data.export.csv': 'strategist',
  'data.export.parquet': 'operator',

  // ML
  'ml.experiments': 'strategist',
  'ml.models.view': 'strategist',
  'ml.models.deploy': 'operator',
  'ml.training': 'operator',

  // Alerts
  'alerts.create': 'strategist',
  'alerts.unlimited': 'operator',

  // Team
  'settings.team': 'operator',
} as const satisfies Record<string, Tier>;

export type FeatureKey = keyof typeof FEATURE_TIERS;
