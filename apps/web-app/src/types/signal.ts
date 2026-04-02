export interface Signal {
  id: string;
  symbol: string;
  instrumentName: string;
  direction: 'buy' | 'sell' | 'hold';
  confidence: number;
  expectedReturn: number | null;
  modelId: string;
  modelName: string;
  modelVersion: string;
  features: { name: string; value: number; importance: number }[];
  generatedAt: string;
  expiresAt: string;
  metadata: {
    lookbackDays: number;
    predictionHorizon: string;
    featureCount: number;
    trainingDateRange: string;
  };
}

export interface SignalFilters {
  direction?: Signal['direction'];
  minConfidence?: number;
  symbol?: string;
}
