export interface CommodityPrice {
  code: string;
  name: string;
  last_price: number;
  currency: string;
  unit: string;
  change_pct: number;
  change_1w_pct: number | null;
  change_1m_pct: number | null;
  updated_at: string;
}

export interface CommodityHistoryPoint {
  date: string;
  price: number;
  volume: number | null;
}

export interface CommodityHistory {
  code: string;
  name: string;
  currency: string;
  unit: string;
  data_points: CommodityHistoryPoint[];
}

export interface CommodityDashboard {
  commodities: CommodityPrice[];
  last_updated: string;
}
