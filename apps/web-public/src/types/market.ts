export interface MarketOverview {
  index_name: string;
  last_value: number;
  change: number;
  change_pct: number;
  volume: number;
  value_traded: number;
  advances: number;
  declines: number;
  unchanged: number;
  timestamp: string;
}

export interface InstrumentResponse {
  symbol: string;
  name: string;
  exchange: string;
  sector: string | null;
  industry: string | null;
  market_cap: number | null;
  is_lq45: boolean;
  board: string;
}

export interface OHLCVBar {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  value: number | null;
}
