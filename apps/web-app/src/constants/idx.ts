export const IDX = {
  SETTLEMENT: 'T+2' as const,
  LOT_SIZE: 100,
  CURRENCY: 'IDR' as const,
  LOCALE: 'id-ID' as const,
  TIMEZONE: 'Asia/Jakarta' as const,

  TICK_SIZES: [
    { maxPrice: 200, tick: 1 },
    { maxPrice: 500, tick: 2 },
    { maxPrice: 2_000, tick: 5 },
    { maxPrice: 5_000, tick: 10 },
    { maxPrice: Infinity, tick: 25 },
  ] as const,

  getTickSize(price: number): number {
    return this.TICK_SIZES.find((t) => price <= t.maxPrice)!.tick;
  },

  TRADING_HOURS: {
    session1: { start: '09:00', end: '11:30', label: 'Session I' },
    lunchBreak: { start: '11:30', end: '13:30', label: 'Lunch Break' },
    session2: { start: '13:30', end: '15:00', label: 'Session II' },
    preOpen: { start: '08:45', end: '09:00', label: 'Pre-Opening' },
    preClose: { start: '14:50', end: '15:00', label: 'Pre-Closing' },
  } as const,

  SHORT_SELLING: false as const,

  FEES: {
    buyCommission: 0.0015,
    sellCommission: 0.0025,
    sellTax: 0.001,
    dividendTax: 0.1,
    capitalGainsTax: 0,
  } as const,

  SYMBOL_FORMAT: /^[A-Z]{4}$/,
  EXCHANGE_SUFFIX: '.JK' as const,

  BOARDS: ['regular', 'development', 'acceleration'] as const,

  SECTORS: [
    'Financials',
    'Basic Materials',
    'Consumer Cyclicals',
    'Consumer Non-Cyclicals',
    'Energy',
    'Healthcare',
    'Industrials',
    'Infrastructures',
    'Properties & Real Estate',
    'Technology',
    'Transportation & Logistics',
  ] as const,

  estimateCost(side: 'buy' | 'sell', price: number, quantity: number) {
    const value = price * quantity;
    const commRate = side === 'buy' ? this.FEES.buyCommission : this.FEES.sellCommission;
    const commission = value * commRate;
    const tax = side === 'sell' ? value * this.FEES.sellTax : 0;
    return { value, commission, tax, total: value + commission };
  },

  AUTO_REJECTION: {
    regular: { upperLimit: 0.25, lowerLimit: -0.25 },
    acceleration: { upperLimit: 0.35, lowerLimit: -0.35 },
    development: { upperLimit: 0.35, lowerLimit: -0.35 },
  } as const,

  getAutoRejectLimits(board: 'regular' | 'development' | 'acceleration', previousClose: number) {
    const limits = this.AUTO_REJECTION[board];
    return {
      upperLimit: Math.round(previousClose * (1 + limits.upperLimit)),
      lowerLimit: Math.round(previousClose * (1 + limits.lowerLimit)),
    };
  },

  CIRCUIT_BREAKER: {
    level1: { dropPct: -5, haltMinutes: 30, label: 'Level 1 Halt' },
    level2: { dropPct: -8, haltMinutes: 30, label: 'Level 2 Halt' },
    level3: { dropPct: -15, haltMinutes: 0, label: 'Trading Suspended' },
  } as const,
} as const;
