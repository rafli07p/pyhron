import { http, HttpResponse } from 'msw';
import { mockMarketOverview, mockInstruments, mockScreenerResults, mockTickerData } from './data/instruments';
import { mockIndexData, mockIndexPerformance } from './data/indices';
import { mockMacroIndicators } from './data/macro';
import { mockCommodities } from './data/commodities';
import { mockArticles } from './data/research';

export const handlers = [
  http.get('/api/v1/market/overview', () => {
    return HttpResponse.json(mockMarketOverview);
  }),

  http.get('/api/v1/market/instruments', ({ request }) => {
    const url = new URL(request.url);
    const sector = url.searchParams.get('sector');
    const lq45Only = url.searchParams.get('lq45_only') === 'true';
    let results = mockInstruments;
    if (sector) results = results.filter((i) => i.sector === sector);
    if (lq45Only) results = results.filter((i) => i.is_lq45);
    return HttpResponse.json(results);
  }),

  http.get('/api/v1/market/ohlcv/:symbol', ({ request }) => {
    const url = new URL(request.url);
    const limit = parseInt(url.searchParams.get('limit') || '365');
    const data = mockIndexData.composite.slice(-limit);
    return HttpResponse.json(data);
  }),

  http.get('/api/v1/screener/screen', ({ request }) => {
    const url = new URL(request.url);
    const limit = parseInt(url.searchParams.get('limit') || '50');
    const sector = url.searchParams.get('sector');
    const lq45Only = url.searchParams.get('lq45_only') === 'true';
    const sortBy = url.searchParams.get('sort_by') || 'market_cap';
    let results = [...mockScreenerResults];
    if (sector) results = results.filter((r) => r.sector === sector);
    if (lq45Only) results = results.filter((r) => r.is_lq45);
    const sortKey = sortBy as keyof typeof results[0];
    results.sort((a, b) => {
      const av = a[sortKey] ?? 0;
      const bv = b[sortKey] ?? 0;
      return (bv as number) - (av as number);
    });
    return HttpResponse.json({
      meta: { total_matches: results.length, filters_applied: {}, sort_by: sortBy, limit },
      results: results.slice(0, limit),
    });
  }),

  http.get('/api/v1/macro/indicators', () => {
    return HttpResponse.json(mockMacroIndicators);
  }),

  http.get('/api/v1/commodities/dashboard', () => {
    return HttpResponse.json({ commodities: mockCommodities, last_updated: new Date().toISOString() });
  }),

  http.get('/api/v1/bonds/government', () => {
    return HttpResponse.json([
      { series: 'FR0098', bond_type: 'Fixed Rate', coupon_rate: 7.125, maturity_date: '2038-06-15', yield_to_maturity: 6.85, price: 102.45, duration: 8.2, outstanding: 45_000_000_000_000 },
      { series: 'FR0097', bond_type: 'Fixed Rate', coupon_rate: 6.50, maturity_date: '2033-02-15', yield_to_maturity: 6.42, price: 100.89, duration: 5.8, outstanding: 38_000_000_000_000 },
      { series: 'FR0096', bond_type: 'Fixed Rate', coupon_rate: 7.00, maturity_date: '2043-02-15', yield_to_maturity: 7.02, price: 99.78, duration: 11.5, outstanding: 52_000_000_000_000 },
    ]);
  }),

  http.get('/api/v1/strategies/', () => {
    return HttpResponse.json([
      { id: 'strat-001', name: 'IDX Momentum', strategy_type: 'momentum', is_enabled: true, parameters: { lookback: 252, holding_period: 21 }, risk_limits: { max_drawdown: 0.15 }, description: '12-1 month momentum on LQ45', created_at: '2025-01-15T00:00:00Z', updated_at: '2026-03-01T00:00:00Z' },
      { id: 'strat-002', name: 'Value-Quality', strategy_type: 'value', is_enabled: true, parameters: { pe_threshold: 15, roe_threshold: 15 }, risk_limits: { max_drawdown: 0.20 }, description: 'Value + quality factor composite', created_at: '2025-03-01T00:00:00Z', updated_at: '2026-03-01T00:00:00Z' },
      { id: 'strat-003', name: 'Pairs Banking', strategy_type: 'pairs', is_enabled: false, parameters: { z_entry: 2.0, z_exit: 0.5 }, risk_limits: { max_drawdown: 0.10 }, description: 'BBCA-BBRI cointegration pairs', created_at: '2025-06-01T00:00:00Z', updated_at: '2026-02-15T00:00:00Z' },
    ]);
  }),

  http.post('/api/v1/auth/login', async ({ request }) => {
    const body = await request.json() as { email: string; password: string };
    if (body.email === 'demo@pyhron.com' && body.password === 'demo1234') {
      return HttpResponse.json({
        access_token: 'mock-access-token-xyz',
        refresh_token: 'mock-refresh-token-xyz',
        token_type: 'bearer',
        expires_in: 3600,
      });
    }
    return HttpResponse.json({ detail: 'Invalid credentials' }, { status: 401 });
  }),

  http.get('/api/v1/auth/me', () => {
    return HttpResponse.json({
      id: 'usr-001',
      email: 'demo@pyhron.com',
      full_name: 'Demo User',
      is_active: true,
      role: 'TRADER',
      tenant_id: 'tenant-001',
      created_at: '2025-01-01T00:00:00Z',
    });
  }),

  http.post('/api/v1/auth/refresh', () => {
    return HttpResponse.json({
      access_token: 'mock-refreshed-access-token',
      refresh_token: 'mock-refreshed-refresh-token',
      token_type: 'bearer',
      expires_in: 3600,
    });
  }),
];
