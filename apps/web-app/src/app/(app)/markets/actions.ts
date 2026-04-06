'use server';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let yf: any = null;
async function getYF() {
  if (!yf) {
    const mod = await import('yahoo-finance2');
    yf = new mod.default();
  }
  return yf;
}

const IDX_STOCKS = [
  'BBCA','BBRI','BMRI','BBNI','TLKM','ASII','UNVR','GOTO',
  'BREN','ICBP','INDF','KLBF','GGRM','HMSP','CPIN',
  'ADRO','PTBA','MEDC','PGAS','ANTM','INCO','MDKA','SMGR',
  'EXCL','ISAT','TBIG','TOWR','JSMR','ACES','JPFA','MNCN',
  'EMTK','ESSA','HRUM','MIKA','BBTN','BRIS','BRPT','INKP',
];

export interface RealStock {
  symbol: string;
  name: string;
  price: number;
  change: number;
  changePct: number;
  volume: number;
  marketCap: number;
  pe: number | null;
  pb: number | null;
  divYield: number | null;
  high52w: number;
  low52w: number;
  sector: string;
}

export async function fetchAllStocks(): Promise<RealStock[]> {
  const yahooFinance = await getYF();
  const results: RealStock[] = [];

  for (let i = 0; i < IDX_STOCKS.length; i += 5) {
    const batch = IDX_STOCKS.slice(i, i + 5);
    const batchResults = await Promise.allSettled(
      batch.map(async (sym) => {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const q: any = await yahooFinance.quote(`${sym}.JK`);
        return {
          symbol: sym,
          name: q.longName ?? q.shortName ?? sym,
          price: q.regularMarketPrice ?? 0,
          change: q.regularMarketChange ?? 0,
          changePct: q.regularMarketChangePercent ?? 0,
          volume: q.regularMarketVolume ?? 0,
          marketCap: q.marketCap ?? 0,
          pe: q.trailingPE ?? null,
          pb: q.priceToBook ?? null,
          divYield: q.dividendYield ? q.dividendYield * 100 : null,
          high52w: q.fiftyTwoWeekHigh ?? 0,
          low52w: q.fiftyTwoWeekLow ?? 0,
          sector: q.sector ?? 'Unknown',
        } satisfies RealStock;
      }),
    );
    for (const r of batchResults) {
      if (r.status === 'fulfilled') results.push(r.value);
    }
    if (i + 5 < IDX_STOCKS.length) await new Promise((r) => setTimeout(r, 150));
  }
  return results.sort((a, b) => b.marketCap - a.marketCap);
}

export async function fetchRealIndices() {
  const yahooFinance = await getYF();
  const indexSymbols = [
    { yahoo: '^JKSE', display: 'IHSG', name: 'Jakarta Composite' },
    { yahoo: '^JKLQ45', display: 'LQ45', name: 'LQ45 Index' },
  ];
  const results = [];
  for (const idx of indexSymbols) {
    try {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const q: any = await yahooFinance.quote(idx.yahoo);
      results.push({
        symbol: idx.display,
        name: idx.name,
        value: q.regularMarketPrice ?? 0,
        change: q.regularMarketChange ?? 0,
        changePct: q.regularMarketChangePercent ?? 0,
      });
    } catch {
      // skip failed
    }
  }
  return results;
}
