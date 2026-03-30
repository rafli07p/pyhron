export interface ScreenerResult {
  symbol: string;
  name: string;
  sector: string | null;
  last_price: number;
  change_pct: number;
  volume: number;
  market_cap: number | null;
  pe_ratio: number | null;
  pbv_ratio: number | null;
  roe: number | null;
  dividend_yield: number | null;
  is_lq45: boolean;
}

export interface ScreenerMeta {
  total_matches: number;
  filters_applied: Record<string, string>;
  sort_by: string;
  limit: number;
}

export interface ScreenerResponse {
  meta: ScreenerMeta;
  results: ScreenerResult[];
}

export interface ScreenerParams {
  sector?: string;
  market_cap_min?: number;
  market_cap_max?: number;
  pe_min?: number;
  pe_max?: number;
  pbv_min?: number;
  pbv_max?: number;
  roe_min?: number;
  dividend_yield_min?: number;
  lq45_only?: boolean;
  sort_by?: 'market_cap' | 'pe_ratio' | 'pbv_ratio' | 'roe' | 'dividend_yield' | 'change_pct' | 'volume';
  limit?: number;
}
