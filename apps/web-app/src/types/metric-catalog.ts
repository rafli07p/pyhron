import type { Tier } from './tier';

export interface MetricCategory {
  id: string;
  name: string;
  description: string;
  count: number;
  subcategories?: MetricCategory[];
}

export interface MetricDefinition {
  id: string;
  name: string;
  category: string;
  subcategory?: string;
  description: string;
  coverage: string;
  historyStart: string;
  updateFrequency: string;
  requiredTier: Tier;
  unit?: string;
  apiEndpoint?: string;
}
