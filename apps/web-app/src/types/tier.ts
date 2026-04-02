export type Tier = 'explorer' | 'strategist' | 'operator';

export interface RiskGuardrails {
  userId: string;
  configuredAt: string;
  configuredBy: string;
  maxPositionPct: number;
  maxPositionValue: number;
  maxOpenPositions: number;
  allowedInstruments: 'all' | 'lq45' | 'idx80' | string[];
  maxDailyLossPct: number;
  maxDailyLossValue: number;
  maxDrawdownPct: number;
  maxOrderSize: number;
  maxOrdersPerDay: number;
  maxOrdersPerMinute: number;
  maxConcurrentStrategies: number;
  maxCapitalPerStrategy: number;
  autoKillDrawdownPct: number;
  autoKillDailyLossPct: number;
  killSwitchCooldown: number;
  stage: 'week1' | 'week2' | 'full';
  stageMultiplier: number;
}

export interface QualificationStatus {
  accountAgeDays: number;
  paperTradingDays: number;
  paperTradesCount: number;
  strategiesDeployed: number;
  emailVerified: boolean;
  kycCompleted: boolean;
  onboardingCallCompleted: boolean;
  guardrailsConfigured: boolean;
  progressPercent: number;
  meetsAutoRequirements: boolean;
}
