import { http, HttpResponse } from 'msw';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const positions = [
  { symbol: 'BBCA', qty: 500, avg_price: 9650, last_price: 9875, lot_size: 100 },
  { symbol: 'BMRI', qty: 1000, avg_price: 5300, last_price: 5450, lot_size: 100 },
  { symbol: 'TLKM', qty: 2000, avg_price: 3850, last_price: 3780, lot_size: 100 },
  { symbol: 'ASII', qty: 800, avg_price: 4500, last_price: 4650, lot_size: 100 },
  { symbol: 'UNVR', qty: 300, avg_price: 2750, last_price: 2680, lot_size: 100 },
];

const enriched = positions.map((p) => {
  const unrealized_pnl = (p.last_price - p.avg_price) * p.qty;
  const unrealized_pnl_pct = ((p.last_price - p.avg_price) / p.avg_price) * 100;
  const market_value = p.last_price * p.qty;
  return {
    symbol: p.symbol,
    quantity: p.qty,
    lots: p.qty / p.lot_size,
    avg_price: p.avg_price,
    last_price: p.last_price,
    market_value,
    cost_basis: p.avg_price * p.qty,
    unrealized_pnl,
    unrealized_pnl_pct: Number(unrealized_pnl_pct.toFixed(2)),
  };
});

const orders = [
  { id: 'ORD-20260401-001', symbol: 'BBCA', side: 'buy', type: 'limit', price: 9850, quantity: 200, filled_qty: 200, status: 'filled', created_at: '2026-04-01T09:15:00Z' },
  { id: 'ORD-20260401-002', symbol: 'TLKM', side: 'sell', type: 'limit', price: 3800, quantity: 500, filled_qty: 300, status: 'partial_fill', created_at: '2026-04-01T10:02:00Z' },
  { id: 'ORD-20260401-003', symbol: 'ASII', side: 'buy', type: 'market', price: 4640, quantity: 100, filled_qty: 100, status: 'filled', created_at: '2026-04-01T10:30:00Z' },
  { id: 'ORD-20260401-004', symbol: 'BMRI', side: 'sell', type: 'limit', price: 5500, quantity: 300, filled_qty: 0, status: 'open', created_at: '2026-04-01T11:00:00Z' },
  { id: 'ORD-20260401-005', symbol: 'GOTO', side: 'buy', type: 'limit', price: 70, quantity: 10000, filled_qty: 0, status: 'cancelled', created_at: '2026-04-01T13:45:00Z' },
];

function generatePnLHistory(days: number) {
  const data = [];
  const now = new Date();
  let cumulative = 0;
  for (let i = days - 1; i >= 0; i--) {
    const date = new Date(now);
    date.setDate(date.getDate() - i);
    if (date.getDay() === 0 || date.getDay() === 6) continue;
    const daily = Math.round((Math.random() - 0.45) * 2_500_000);
    cumulative += daily;
    data.push({
      date: date.toISOString().slice(0, 10),
      daily_pnl: daily,
      cumulative_pnl: cumulative,
    });
  }
  return data;
}

export const portfolioHandlers = [
  // Positions
  http.get(`${API_BASE}/v1/trading/positions`, () => {
    const totalValue = enriched.reduce((s, p) => s + p.market_value, 0);
    const totalPnl = enriched.reduce((s, p) => s + p.unrealized_pnl, 0);
    return HttpResponse.json({
      positions: enriched,
      total_market_value: totalValue,
      total_unrealized_pnl: totalPnl,
      cash_balance: 125_000_000,
      updated_at: new Date().toISOString(),
    });
  }),

  // Orders list
  http.get(`${API_BASE}/v1/trading/orders`, () => {
    return HttpResponse.json({ orders, total: orders.length });
  }),

  // Create order
  http.post(`${API_BASE}/v1/trading/orders`, async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json(
      {
        id: `ORD-${Date.now()}`,
        symbol: body.symbol,
        side: body.side,
        type: body.type || 'limit',
        price: body.price,
        quantity: body.quantity,
        filled_qty: 0,
        status: 'new',
        created_at: new Date().toISOString(),
      },
      { status: 201 },
    );
  }),

  // P&L history
  http.get(`${API_BASE}/v1/trading/pnl`, () => {
    const history = generatePnLHistory(30);
    return HttpResponse.json({
      history,
      period_return_pct: 3.24,
      period_sharpe: 1.12,
    });
  }),
];
