// src/mocks/terminal-data.ts
// Deterministic mock data for all terminal pages. No Math.random().

// ═══ PORTFOLIO ═══
export const PORTFOLIO = {
  nav: 1_234_567_890,
  dayPnl: 28_456_789,
  dayPnlPct: 2.34,
  totalReturn: 12.34,
  sharpe: 1.84,
  winRate: 62.3,
  openPositions: 8,
  invested: 892_000_000,
  cash: 342_567_890,
  var95: -1.2,
  cvar95: -1.8,
  maxDrawdown: -8.3,
  maxDrawdownDays: 23,
  beta: 0.82,
  trackingError: 3.45,
  infoRatio: 1.21,
  sortino: 2.31,
  calmar: 1.42,
} as const;

// ═══ POSITIONS ═══
export const POSITIONS = [
  { symbol: 'BBCA', name: 'Bank Central Asia', qty: 500, lots: 5, avgPrice: 9650, currentPrice: 9875, sector: 'Financials', weight: 28.2 },
  { symbol: 'BMRI', name: 'Bank Mandiri', qty: 300, lots: 3, avgPrice: 6100, currentPrice: 6225, sector: 'Financials', weight: 10.7 },
  { symbol: 'TLKM', name: 'Telkom Indonesia', qty: 200, lots: 2, avgPrice: 3900, currentPrice: 3850, sector: 'Telecom', weight: 4.4 },
  { symbol: 'ASII', name: 'Astra International', qty: 1000, lots: 10, avgPrice: 4700, currentPrice: 4750, sector: 'Consumer', weight: 27.2 },
  { symbol: 'UNVR', name: 'Unilever Indonesia', qty: 400, lots: 4, avgPrice: 4200, currentPrice: 4150, sector: 'Consumer', weight: 9.5 },
  { symbol: 'BBRI', name: 'Bank Rakyat Indonesia', qty: 600, lots: 6, avgPrice: 4800, currentPrice: 4850, sector: 'Financials', weight: 16.6 },
  { symbol: 'GOTO', name: 'GoTo Gojek Tokopedia', qty: 5000, lots: 50, avgPrice: 85, currentPrice: 82, sector: 'Technology', weight: 2.3 },
  { symbol: 'BREN', name: 'Barito Renewables', qty: 200, lots: 2, avgPrice: 7900, currentPrice: 8250, sector: 'Energy', weight: 9.4 },
] as const;

// ═══ INDICES ═══
export const INDICES = [
  { symbol: 'IHSG', name: 'Jakarta Composite', value: 7234.56, change: 32.45, changePct: 0.45 },
  { symbol: 'LQ45', name: 'LQ45 Index', value: 985.23, change: -5.12, changePct: -0.52 },
  { symbol: 'IDX30', name: 'IDX30 Index', value: 482.18, change: 2.78, changePct: 0.58 },
  { symbol: 'JII', name: 'Jakarta Islamic', value: 548.92, change: -3.21, changePct: -0.58 },
  { symbol: 'IDX80', name: 'IDX80 Index', value: 132.45, change: 0.87, changePct: 0.66 },
  { symbol: 'IDXHIDIV20', name: 'High Dividend 20', value: 423.67, change: 1.23, changePct: 0.29 },
] as const;

// ═══ STRATEGIES ═══
export const STRATEGIES = [
  { id: '1', name: 'MomentumIDX', status: 'running' as const, type: 'Momentum', pnl: 4.2, sharpe: 1.84, maxDd: -8.3, trades: 28, winRate: 64, mode: 'paper' as const, capital: 250_000_000 },
  { id: '2', name: 'PairsTrade BBCA-BMRI', status: 'paused' as const, type: 'StatArb', pnl: 1.8, sharpe: 1.21, maxDd: -5.1, trades: 12, winRate: 58, mode: 'paper' as const, capital: 150_000_000 },
  { id: '3', name: 'ML Signal Alpha', status: 'running' as const, type: 'ML', pnl: 6.7, sharpe: 2.15, maxDd: -4.2, trades: 45, winRate: 71, mode: 'paper' as const, capital: 300_000_000 },
  { id: '4', name: 'MeanReversion', status: 'error' as const, type: 'MeanRev', pnl: -0.3, sharpe: -0.21, maxDd: -12.1, trades: 5, winRate: 40, mode: 'paper' as const, capital: 50_000_000 },
  { id: '5', name: 'ValueIDX LQ45', status: 'running' as const, type: 'Value', pnl: 3.1, sharpe: 1.45, maxDd: -6.8, trades: 32, winRate: 59, mode: 'paper' as const, capital: 200_000_000 },
  { id: '6', name: 'SectorRotation', status: 'paused' as const, type: 'Sector', pnl: 2.4, sharpe: 0.98, maxDd: -9.2, trades: 18, winRate: 55, mode: 'paper' as const, capital: 180_000_000 },
  { id: '7', name: 'BreakoutScanner', status: 'running' as const, type: 'Technical', pnl: 5.5, sharpe: 1.72, maxDd: -7.1, trades: 56, winRate: 62, mode: 'paper' as const, capital: 120_000_000 },
  { id: '8', name: 'VolTargeting', status: 'paused' as const, type: 'RiskParity', pnl: 1.2, sharpe: 0.85, maxDd: -3.4, trades: 8, winRate: 50, mode: 'paper' as const, capital: 100_000_000 },
] as const;

// ═══ RECENT ORDERS ═══
export const RECENT_ORDERS = [
  { id: 'O-1001', time: '14:32', side: 'BUY' as const, symbol: 'BBCA', qty: 100, price: 9875, status: 'filled' as const, strategy: 'MomentumIDX' },
  { id: 'O-1002', time: '14:28', side: 'SELL' as const, symbol: 'TLKM', qty: 200, price: 3850, status: 'filled' as const, strategy: 'MomentumIDX' },
  { id: 'O-1003', time: '14:15', side: 'BUY' as const, symbol: 'BMRI', qty: 300, price: 6225, status: 'partial' as const, strategy: 'PairsTrade' },
  { id: 'O-1004', time: '13:45', side: 'BUY' as const, symbol: 'ASII', qty: 1000, price: 4750, status: 'filled' as const, strategy: 'ValueIDX' },
  { id: 'O-1005', time: '11:22', side: 'SELL' as const, symbol: 'GOTO', qty: 2000, price: 82, status: 'filled' as const, strategy: 'MeanRev' },
  { id: 'O-1006', time: '10:55', side: 'BUY' as const, symbol: 'BREN', qty: 200, price: 8250, status: 'filled' as const, strategy: 'MLSignal' },
  { id: 'O-1007', time: '10:32', side: 'BUY' as const, symbol: 'BBRI', qty: 600, price: 4850, status: 'filled' as const, strategy: 'SectorRot' },
  { id: 'O-1008', time: '09:45', side: 'SELL' as const, symbol: 'UNVR', qty: 100, price: 4150, status: 'filled' as const, strategy: 'ValueIDX' },
] as const;

// ═══ SECTORS ═══
export const SECTORS = [
  { name: 'Financials', change: 1.2, weight: 35 },
  { name: 'Consumer', change: -0.5, weight: 15 },
  { name: 'Energy', change: 2.1, weight: 10 },
  { name: 'Industrials', change: 0.3, weight: 12 },
  { name: 'Technology', change: -1.8, weight: 8 },
  { name: 'Healthcare', change: 0.7, weight: 5 },
  { name: 'Materials', change: -0.2, weight: 6 },
  { name: 'Infra', change: 1.5, weight: 5 },
  { name: 'Property', change: -0.8, weight: 4 },
] as const;

// ═══ MARKET BREADTH ═══
export const MARKET_BREADTH = { advancing: 412, declining: 298, unchanged: 90 } as const;

// ═══ MONTHLY RETURNS ═══
export const MONTHLY_RETURNS = [
  { month: 'Jul', portfolio: 2.1, benchmark: 1.8 },
  { month: 'Aug', portfolio: -0.8, benchmark: -1.2 },
  { month: 'Sep', portfolio: 3.4, benchmark: 2.1 },
  { month: 'Oct', portfolio: 1.2, benchmark: 0.5 },
  { month: 'Nov', portfolio: -1.5, benchmark: -2.3 },
  { month: 'Dec', portfolio: 4.2, benchmark: 3.1 },
  { month: 'Jan', portfolio: 2.8, benchmark: 1.9 },
  { month: 'Feb', portfolio: -0.3, benchmark: -0.8 },
  { month: 'Mar', portfolio: 1.9, benchmark: 1.5 },
  { month: 'Apr', portfolio: 0.8, benchmark: 0.4 },
] as const;

// ═══ ALERTS ═══
export const ALERTS = [
  { id: 'A1', metric: 'Price', symbol: 'BBCA', condition: 'crosses above', value: 10000, status: 'active' as const, triggered: false },
  { id: 'A2', metric: 'RSI(14)', symbol: 'GOTO', condition: 'drops below', value: 30, status: 'active' as const, triggered: true, triggeredAt: '2h ago' },
  { id: 'A3', metric: 'Volume', symbol: 'BREN', condition: 'exceeds', value: 100_000_000, status: 'active' as const, triggered: false },
  { id: 'A4', metric: 'Day Change %', symbol: 'IHSG', condition: 'drops below', value: -3, status: 'active' as const, triggered: false },
  { id: 'A5', metric: 'P/E Ratio', symbol: 'TLKM', condition: 'drops below', value: 14, status: 'paused' as const, triggered: false },
] as const;

// ═══ PAPER TRADING ═══
export const PAPER_TRADING = {
  connection: 'Connected', broker: 'Alpaca Paper', activeStrategies: 4,
  totalTrades: 205, pnlMtd: 3_456_789, pnlMtdPct: 2.8, daysActive: 37,
  avgTradesDay: 5.5, avgHoldMin: 187, largestWin: 12_450_000, largestLoss: -5_200_000,
  profitFactor: 1.78, sharpe: 1.84, winRate: 62.3,
} as const;

// ═══ GUARDRAILS ═══
export const GUARDRAILS = {
  maxPosition: { current: 500_000_000, limit: 2_000_000_000 },
  dailyLoss: { current: -12_000_000, limit: -100_000_000 },
  openOrders: { current: 3, limit: 10 },
  maxOrderValue: { current: 50_000_000, limit: 200_000_000 },
  circuitBreaker: 'armed' as const,
  killSwitch: 'inactive' as const,
} as const;

// ═══ CHART DATA GENERATORS (deterministic — no Math.random) ═══

export function generateEquityCurve(days = 90) {
  const start = new Date('2026-01-05');
  const startEquity = 1_100_000_000;
  let peak = startEquity;
  const data: Array<{ date: string; equity: number; benchmark: number; drawdown: number }> = [];

  for (let i = 0; i < days; i++) {
    const d = new Date(start);
    d.setDate(d.getDate() + i);
    if (d.getDay() === 0 || d.getDay() === 6) continue;

    const trend = i * 1_500_000;
    const cycle = Math.sin(i * 0.15) * 30_000_000;
    const noise = Math.sin(i * 2.3 + 7) * 10_000_000;
    const equity = Math.round(startEquity + trend + cycle + noise);
    peak = Math.max(peak, equity);
    const drawdown = Math.round(((equity - peak) / peak) * 10000) / 100;
    const benchmark = Math.round(7000 + i * 3 + Math.sin(i * 0.12) * 100);

    data.push({ date: d.toISOString().split('T')[0]!, equity, benchmark, drawdown });
  }
  return data;
}

export function generateOHLCV(basePrice: number, days = 120) {
  const start = new Date('2025-12-01');
  const data: Array<{ date: string; open: number; high: number; low: number; close: number; volume: number }> = [];
  let price = basePrice;

  for (let i = 0; i < days; i++) {
    const d = new Date(start);
    d.setDate(d.getDate() + i);
    if (d.getDay() === 0 || d.getDay() === 6) continue;

    const change = Math.sin(i * 1.7 + 3) * basePrice * 0.015 + Math.sin(i * 0.3) * basePrice * 0.008;
    const open = Math.round(price);
    const close = Math.round(price + change);
    const high = Math.round(Math.max(open, close) + Math.abs(Math.sin(i * 2.1)) * basePrice * 0.005);
    const low = Math.round(Math.min(open, close) - Math.abs(Math.cos(i * 1.9)) * basePrice * 0.005);
    const volume = Math.round(20_000_000 + Math.abs(Math.sin(i * 0.8)) * 30_000_000);

    data.push({ date: d.toISOString().split('T')[0]!, open, high, low, close, volume });
    price = close;
  }
  return data;
}

export function generateSparkline(points = 20, start = 100, volatility = 2): number[] {
  const data: number[] = [];
  let val = start;
  for (let i = 0; i < points; i++) {
    val += Math.sin(i * 1.3 + 2) * volatility + Math.sin(i * 0.4) * volatility * 0.5;
    data.push(Math.round(val * 100) / 100);
  }
  return data;
}

export function getInstrumentDetail(symbol: string) {
  const instruments: Record<string, {
    symbol: string; name: string; sector: string;
    marketCap: number; peRatio: number; pbRatio: number;
    divYield: number; roe: number;
    high52w: number; low52w: number; avgVolume30d: number;
    currentPrice: number; prevClose: number; change: number; changePct: number;
    open: number; dayHigh: number; dayLow: number; volume: number;
    board: string; lotSize: number; tickSize: number;
    description: string;
  }> = {
    BBCA: {
      symbol: 'BBCA', name: 'Bank Central Asia Tbk', sector: 'Financials',
      marketCap: 1_215_000_000_000_000, peRatio: 26.4, pbRatio: 4.8,
      divYield: 1.2, roe: 18.2,
      high52w: 10_525, low52w: 8_375, avgVolume30d: 42_500_000,
      currentPrice: 9875, prevClose: 9750, change: 125, changePct: 1.28,
      open: 9775, dayHigh: 9900, dayLow: 9750, volume: 45_200_000,
      board: 'Regular', lotSize: 100, tickSize: 25,
      description: 'PT Bank Central Asia Tbk is Indonesia\'s largest private bank by market capitalization.',
    },
    BMRI: {
      symbol: 'BMRI', name: 'Bank Mandiri Tbk', sector: 'Financials',
      marketCap: 580_000_000_000_000, peRatio: 12.8, pbRatio: 2.3,
      divYield: 3.8, roe: 19.5,
      high52w: 7_100, low52w: 5_250, avgVolume30d: 38_000_000,
      currentPrice: 6225, prevClose: 6175, change: 50, changePct: 0.81,
      open: 6200, dayHigh: 6275, dayLow: 6175, volume: 34_500_000,
      board: 'Regular', lotSize: 100, tickSize: 25,
      description: 'PT Bank Mandiri (Persero) Tbk is Indonesia\'s largest state-owned bank.',
    },
    TLKM: {
      symbol: 'TLKM', name: 'Telkom Indonesia Tbk', sector: 'Telecom',
      marketCap: 380_000_000_000_000, peRatio: 15.2, pbRatio: 3.1,
      divYield: 4.2, roe: 20.1,
      high52w: 4_300, low52w: 3_200, avgVolume30d: 65_000_000,
      currentPrice: 3850, prevClose: 3890, change: -40, changePct: -1.03,
      open: 3880, dayHigh: 3900, dayLow: 3825, volume: 67_800_000,
      board: 'Regular', lotSize: 100, tickSize: 5,
      description: 'PT Telkom Indonesia (Persero) Tbk is Indonesia\'s largest telecommunications company.',
    },
    GOTO: {
      symbol: 'GOTO', name: 'GoTo Gojek Tokopedia Tbk', sector: 'Technology',
      marketCap: 95_000_000_000_000, peRatio: -42.5, pbRatio: 1.8,
      divYield: 0, roe: -4.2,
      high52w: 112, low52w: 58, avgVolume30d: 850_000_000,
      currentPrice: 82, prevClose: 85, change: -3, changePct: -3.53,
      open: 84, dayHigh: 86, dayLow: 80, volume: 892_100_000,
      board: 'Regular', lotSize: 100, tickSize: 1,
      description: 'PT GoTo Gojek Tokopedia Tbk is Indonesia\'s largest digital ecosystem.',
    },
  };
  return instruments[symbol] ?? instruments['BBCA']!;
}

// ═══ SCREENER DATA ═══
export function generateScreenerData(count = 40) {
  const stocks = [
    { symbol: 'BBCA', name: 'Bank Central Asia', sector: 'Financials', basePrice: 9875 },
    { symbol: 'BBRI', name: 'Bank Rakyat Indonesia', sector: 'Financials', basePrice: 4850 },
    { symbol: 'BMRI', name: 'Bank Mandiri', sector: 'Financials', basePrice: 6225 },
    { symbol: 'TLKM', name: 'Telkom Indonesia', sector: 'Telecom', basePrice: 3850 },
    { symbol: 'ASII', name: 'Astra International', sector: 'Consumer', basePrice: 4750 },
    { symbol: 'UNVR', name: 'Unilever Indonesia', sector: 'Consumer', basePrice: 4150 },
    { symbol: 'GOTO', name: 'GoTo Gojek Tokopedia', sector: 'Technology', basePrice: 82 },
    { symbol: 'BREN', name: 'Barito Renewables', sector: 'Energy', basePrice: 8250 },
    { symbol: 'PANI', name: 'Pantai Indah Kapuk', sector: 'Property', basePrice: 14250 },
    { symbol: 'EMTK', name: 'Elang Mahkota', sector: 'Technology', basePrice: 440 },
    { symbol: 'ICBP', name: 'Indofood CBP', sector: 'Consumer', basePrice: 11200 },
    { symbol: 'INDF', name: 'Indofood Sukses', sector: 'Consumer', basePrice: 6850 },
    { symbol: 'KLBF', name: 'Kalbe Farma', sector: 'Healthcare', basePrice: 1575 },
    { symbol: 'PGAS', name: 'Perusahaan Gas Negara', sector: 'Energy', basePrice: 1465 },
    { symbol: 'SMGR', name: 'Semen Indonesia', sector: 'Materials', basePrice: 4100 },
    { symbol: 'ADRO', name: 'Adaro Energy', sector: 'Energy', basePrice: 2680 },
    { symbol: 'ANTM', name: 'Aneka Tambang', sector: 'Materials', basePrice: 1320 },
    { symbol: 'BBNI', name: 'Bank Negara Indonesia', sector: 'Financials', basePrice: 4925 },
    { symbol: 'CPIN', name: 'Charoen Pokphand', sector: 'Consumer', basePrice: 4870 },
    { symbol: 'EXCL', name: 'XL Axiata', sector: 'Telecom', basePrice: 2340 },
    { symbol: 'GGRM', name: 'Gudang Garam', sector: 'Consumer', basePrice: 15200 },
    { symbol: 'HMSP', name: 'HM Sampoerna', sector: 'Consumer', basePrice: 730 },
    { symbol: 'INCO', name: 'Vale Indonesia', sector: 'Materials', basePrice: 3780 },
    { symbol: 'ISAT', name: 'Indosat Ooredoo', sector: 'Telecom', basePrice: 7425 },
    { symbol: 'JPFA', name: 'Japfa Comfeed', sector: 'Consumer', basePrice: 1215 },
    { symbol: 'JSMR', name: 'Jasa Marga', sector: 'Infra', basePrice: 4520 },
    { symbol: 'MDKA', name: 'Merdeka Copper Gold', sector: 'Materials', basePrice: 1890 },
    { symbol: 'MEDC', name: 'Medco Energi', sector: 'Energy', basePrice: 1175 },
    { symbol: 'MIKA', name: 'Mitra Keluarga', sector: 'Healthcare', basePrice: 2580 },
    { symbol: 'PTBA', name: 'Bukit Asam', sector: 'Energy', basePrice: 2560 },
    { symbol: 'TBIG', name: 'Tower Bersama', sector: 'Infra', basePrice: 1850 },
    { symbol: 'TOWR', name: 'Sarana Menara', sector: 'Infra', basePrice: 940 },
    { symbol: 'ACES', name: 'Ace Hardware', sector: 'Consumer', basePrice: 735 },
    { symbol: 'BBTN', name: 'Bank Tabungan Negara', sector: 'Financials', basePrice: 1355 },
    { symbol: 'BRIS', name: 'Bank Syariah Indonesia', sector: 'Financials', basePrice: 2730 },
    { symbol: 'BRPT', name: 'Barito Pacific', sector: 'Materials', basePrice: 915 },
    { symbol: 'ESSA', name: 'Surya Esa Perkasa', sector: 'Energy', basePrice: 1275 },
    { symbol: 'HRUM', name: 'Harum Energy', sector: 'Energy', basePrice: 1650 },
    { symbol: 'INKP', name: 'Indah Kiat Pulp', sector: 'Materials', basePrice: 8575 },
    { symbol: 'MNCN', name: 'Media Nusantara', sector: 'Technology', basePrice: 820 },
  ];

  return stocks.slice(0, count).map((s, i) => ({
    symbol: s.symbol,
    name: s.name,
    price: s.basePrice,
    change: Math.round(Math.sin(i * 1.7 + 3) * 300) / 100,
    volume: Math.round(10_000_000 + Math.abs(Math.sin(i * 0.8)) * 90_000_000),
    marketCap: Math.round(s.basePrice * (1_000_000 + i * 500_000) * 100),
    pe: Math.round((10 + Math.sin(i * 0.5) * 15 + 10) * 10) / 10,
    pb: Math.round((1 + Math.sin(i * 0.7) * 3 + 2) * 10) / 10,
    divYield: Math.round(Math.abs(Math.sin(i * 0.9)) * 50) / 10,
    sector: s.sector,
  }));
}
