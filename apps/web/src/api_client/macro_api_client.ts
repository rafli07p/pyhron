import axios from 'axios';

const api = axios.create({ baseURL: '/api/v1' });

export interface MacroIndicator {
  indicatorCode: string;
  indicatorName: string;
  value: number;
  unit: string;
  observationDate: string;
  changePct: number | null;
}

export interface YieldCurvePoint {
  tenor: string;
  tenorMonths: number;
  yieldPct: number;
  changeBps: number;
}

export interface PolicyEvent {
  eventDate: string;
  title: string;
  category: string;
  impact: string;
  description: string;
}

export const macroApi = {
  getIndicators: () =>
    api.get<MacroIndicator[]>('/macro/indicators'),

  getIndicatorHistory: (code: string, params?: { days?: number }) =>
    api.get(`/macro/indicators/${code}/history`, { params }),

  getYieldCurve: (params?: { date?: string }) =>
    api.get<YieldCurvePoint[]>('/macro/yield-curve', { params }),

  getPolicyCalendar: (params?: { daysAhead?: number }) =>
    api.get<PolicyEvent[]>('/macro/policy-calendar', { params }),
};
