import axios from 'axios';

const api = axios.create({ baseURL: '/api/v1' });

export interface CommodityPrice {
  commodityCode: string;
  commodityName: string;
  price: number;
  changePct: number;
  currency: string;
  unit: string;
  priceDate: string;
}

export interface CommodityImpact {
  commodityCode: string;
  impactedSymbols: Array<{
    symbol: string;
    sensitivity: number;
    estimatedImpactPct: number;
  }>;
}

export const commodityApi = {
  getCommodities: () =>
    api.get<CommodityPrice[]>('/commodities'),

  getCommodityHistory: (code: string, params?: { days?: number }) =>
    api.get(`/commodities/${code}/history`, { params }),

  getImpactAnalysis: (code: string) =>
    api.get<CommodityImpact>(`/commodity-impact/analysis/${code}`),

  getAlerts: () =>
    api.get('/commodity-impact/alerts'),

  getFixedIncome: () =>
    api.get('/fixed-income/government-bonds'),

  getYieldCurve: () =>
    api.get('/fixed-income/yield-curve'),
};
