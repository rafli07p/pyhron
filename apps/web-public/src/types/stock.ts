export interface StockProfile {
  symbol: string;
  name: string;
  exchange: string;
  sector: string | null;
  industry: string | null;
  listing_date: string | null;
  market_cap: number | null;
  last_price: number | null;
  shares_outstanding: number | null;
  is_lq45: boolean;
  description: string | null;
}

export interface FinancialSummary {
  symbol: string;
  period: string;
  revenue: number | null;
  net_income: number | null;
  total_assets: number | null;
  total_equity: number | null;
  eps: number | null;
  pe_ratio: number | null;
  pbv_ratio: number | null;
  roe: number | null;
  der: number | null;
}

export interface CorporateAction {
  symbol: string;
  action_type: string;
  ex_date: string;
  record_date: string | null;
  description: string;
  value: number | null;
}

export interface OwnershipEntry {
  holder_name: string;
  holder_type: string;
  shares_held: number;
  ownership_pct: number;
  change_from_prior: number | null;
}
