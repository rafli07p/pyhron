import type { CommodityPrice } from '@/types/commodity';

export const mockCommodities: CommodityPrice[] = [
  { code: 'CPO', name: 'Crude Palm Oil', last_price: 4125, currency: 'MYR', unit: 'MT', change_pct: 1.23, change_1w_pct: 2.45, change_1m_pct: -3.12, updated_at: '2026-03-28T00:00:00Z' },
  { code: 'COAL_HBA', name: 'Coal HBA Reference Price', last_price: 128.5, currency: 'USD', unit: 'MT', change_pct: -0.78, change_1w_pct: -1.23, change_1m_pct: -5.45, updated_at: '2026-03-28T00:00:00Z' },
  { code: 'NICKEL_LME', name: 'Nickel LME', last_price: 16850, currency: 'USD', unit: 'MT', change_pct: 2.34, change_1w_pct: 3.78, change_1m_pct: 8.92, updated_at: '2026-03-28T00:00:00Z' },
  { code: 'TIN_LME', name: 'Tin LME', last_price: 28400, currency: 'USD', unit: 'MT', change_pct: 0.89, change_1w_pct: 1.56, change_1m_pct: 4.23, updated_at: '2026-03-28T00:00:00Z' },
  { code: 'RUBBER', name: 'Rubber TSR20', last_price: 1.58, currency: 'USD', unit: 'kg', change_pct: -1.25, change_1w_pct: -2.34, change_1m_pct: -6.78, updated_at: '2026-03-28T00:00:00Z' },
  { code: 'GOLD', name: 'Gold Spot', last_price: 2185, currency: 'USD', unit: 'oz', change_pct: 0.45, change_1w_pct: 1.23, change_1m_pct: 3.45, updated_at: '2026-03-28T00:00:00Z' },
];
