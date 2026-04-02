export interface RiskMetrics {
  portfolioValue: number;
  cashBalance: number;
  investedValue: number;
  var95_1d: number;
  var99_1d: number;
  cvar95_1d: number;
  maxDrawdown: number;
  maxDrawdownDuration: number;
  currentDrawdown: number;
  currentDrawdownDuration: number;
  sharpeRatio: number;
  sortinoRatio: number;
  calmarRatio: number;
  beta: number;
  alpha: number;
  trackingError: number | null;
  informationRatio: number | null;
  sectorExposure: { sector: string; weight: number; value: number }[];
  topConcentration: { symbol: string; weight: number; value: number; beta: number }[];
  correlationMatrix: {
    symbols: string[];
    matrix: number[][];
  };
  stressScenarios: {
    name: string;
    description: string;
    impact: number;
    varChange: number;
  }[];
  updatedAt: string;
}
