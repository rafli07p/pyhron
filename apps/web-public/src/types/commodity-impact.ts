export interface StockImpact {
  symbol: string;
  name: string;
  sector: string | null;
  correlation: number;
  beta: number;
  revenue_exposure_pct: number | null;
}

export interface CommodityImpactAnalysis {
  commodity_code: string;
  commodity_name: string;
  change_pct_30d: number | null;
  impacted_stocks: StockImpact[];
  analysis_date: string;
}

export interface SensitivityCell {
  symbol: string;
  commodity_code: string;
  beta: number;
  correlation: number;
  r_squared: number;
}

export interface SensitivityMatrix {
  commodities: string[];
  stocks: string[];
  cells: SensitivityCell[];
  computed_at: string;
}
