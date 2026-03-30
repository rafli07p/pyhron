import type { MacroIndicator } from '@/types/macro';

export const mockMacroIndicators: MacroIndicator[] = [
  { code: 'BI_RATE', name: 'BI 7-Day Reverse Repo Rate', latest_value: 5.75, unit: '%', period: '2026-03', source: 'Bank Indonesia', updated_at: '2026-03-20T00:00:00Z' },
  { code: 'GDP_GROWTH', name: 'GDP Growth (YoY)', latest_value: 5.05, unit: '%', period: '2025-Q4', source: 'BPS', updated_at: '2026-02-05T00:00:00Z' },
  { code: 'CPI_YOY', name: 'CPI Inflation (YoY)', latest_value: 2.81, unit: '%', period: '2026-02', source: 'BPS', updated_at: '2026-03-01T00:00:00Z' },
  { code: 'IDR_USD', name: 'IDR/USD Exchange Rate', latest_value: 15842, unit: 'IDR', period: '2026-03-28', source: 'Bank Indonesia', updated_at: '2026-03-28T00:00:00Z' },
  { code: 'TRADE_BAL', name: 'Trade Balance', latest_value: 3.56, unit: 'USD Billion', period: '2026-02', source: 'BPS', updated_at: '2026-03-15T00:00:00Z' },
  { code: 'FDI', name: 'Foreign Direct Investment', latest_value: 12.4, unit: 'USD Billion', period: '2025-Q4', source: 'BKPM', updated_at: '2026-01-28T00:00:00Z' },
];
