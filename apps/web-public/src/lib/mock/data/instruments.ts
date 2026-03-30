import type { MarketOverview, InstrumentResponse } from '@/types/market';
import type { ScreenerResult } from '@/types/screener';

export const mockMarketOverview: MarketOverview = {
  index_name: 'IHSG',
  last_value: 7245.32,
  change: 42.18,
  change_pct: 0.59,
  volume: 12_450_000_000,
  value_traded: 8_750_000_000_000,
  advances: 245,
  declines: 198,
  unchanged: 87,
  timestamp: new Date().toISOString(),
};

const stockData = [
  { symbol: 'BBCA', name: 'Bank Central Asia Tbk', sector: 'Financials', market_cap: 1_200_000_000_000_000, price: 9875, change: 1.25, pe: 25.3, pb: 4.8, roe: 19.2, dy: 1.1 },
  { symbol: 'BBRI', name: 'Bank Rakyat Indonesia Tbk', sector: 'Financials', market_cap: 850_000_000_000_000, price: 5525, change: -0.45, pe: 14.2, pb: 2.6, roe: 18.5, dy: 3.2 },
  { symbol: 'TLKM', name: 'Telkom Indonesia Tbk', sector: 'Communication Services', market_cap: 380_000_000_000_000, price: 3840, change: 0.79, pe: 16.8, pb: 3.1, roe: 18.9, dy: 4.1 },
  { symbol: 'ASII', name: 'Astra International Tbk', sector: 'Consumer Discretionary', market_cap: 280_000_000_000_000, price: 6925, change: -1.12, pe: 12.5, pb: 1.8, roe: 14.2, dy: 5.8 },
  { symbol: 'BMRI', name: 'Bank Mandiri Tbk', sector: 'Financials', market_cap: 650_000_000_000_000, price: 6975, change: 0.87, pe: 11.8, pb: 2.1, roe: 17.8, dy: 4.5 },
  { symbol: 'UNVR', name: 'Unilever Indonesia Tbk', sector: 'Consumer Staples', market_cap: 145_000_000_000_000, price: 3800, change: -2.31, pe: 28.5, pb: 35.2, roe: 120.5, dy: 3.5 },
  { symbol: 'BBNI', name: 'Bank Negara Indonesia Tbk', sector: 'Financials', market_cap: 180_000_000_000_000, price: 4850, change: 1.46, pe: 8.9, pb: 1.2, roe: 13.8, dy: 5.2 },
  { symbol: 'BRIS', name: 'Bank Syariah Indonesia Tbk', sector: 'Financials', market_cap: 75_000_000_000_000, price: 2560, change: 2.40, pe: 18.5, pb: 3.2, roe: 17.1, dy: 0.8 },
  { symbol: 'INDF', name: 'Indofood Sukses Makmur Tbk', sector: 'Consumer Staples', market_cap: 55_000_000_000_000, price: 6275, change: 0.32, pe: 9.8, pb: 1.4, roe: 14.1, dy: 4.8 },
  { symbol: 'ICBP', name: 'Indofood CBP Sukses Makmur', sector: 'Consumer Staples', market_cap: 95_000_000_000_000, price: 8150, change: -0.61, pe: 18.2, pb: 3.5, roe: 19.4, dy: 2.1 },
  { symbol: 'KLBF', name: 'Kalbe Farma Tbk', sector: 'Health Care', market_cap: 72_000_000_000_000, price: 1535, change: 0.99, pe: 22.1, pb: 3.8, roe: 17.2, dy: 2.5 },
  { symbol: 'HMSP', name: 'HM Sampoerna Tbk', sector: 'Consumer Staples', market_cap: 58_000_000_000_000, price: 500, change: -1.57, pe: 10.2, pb: 4.5, roe: 44.1, dy: 6.8 },
  { symbol: 'GGRM', name: 'Gudang Garam Tbk', sector: 'Consumer Staples', market_cap: 52_000_000_000_000, price: 27000, change: 0.19, pe: 15.8, pb: 1.2, roe: 7.8, dy: 2.8 },
  { symbol: 'ADRO', name: 'Adaro Energy Indonesia Tbk', sector: 'Energy', market_cap: 120_000_000_000_000, price: 3750, change: 3.45, pe: 8.2, pb: 1.9, roe: 23.1, dy: 6.2 },
  { symbol: 'ITMG', name: 'Indo Tambangraya Megah Tbk', sector: 'Energy', market_cap: 35_000_000_000_000, price: 31000, change: 2.98, pe: 6.5, pb: 2.8, roe: 43.2, dy: 7.0 },
  { symbol: 'PTBA', name: 'Bukit Asam Tbk', sector: 'Energy', market_cap: 42_000_000_000_000, price: 3650, change: 1.67, pe: 7.1, pb: 2.1, roe: 29.5, dy: 5.5 },
  { symbol: 'ANTM', name: 'Aneka Tambang Tbk', sector: 'Materials', market_cap: 45_000_000_000_000, price: 1875, change: -0.80, pe: 12.3, pb: 1.6, roe: 13.0, dy: 2.1 },
  { symbol: 'INCO', name: 'Vale Indonesia Tbk', sector: 'Materials', market_cap: 62_000_000_000_000, price: 6350, change: 1.20, pe: 18.9, pb: 2.4, roe: 12.8, dy: 1.5 },
  { symbol: 'MDKA', name: 'Merdeka Copper Gold Tbk', sector: 'Materials', market_cap: 85_000_000_000_000, price: 3580, change: -1.93, pe: 45.2, pb: 5.8, roe: 12.9, dy: 0.0 },
  { symbol: 'EXCL', name: 'XL Axiata Tbk', sector: 'Communication Services', market_cap: 38_000_000_000_000, price: 2820, change: 0.71, pe: 22.4, pb: 1.8, roe: 8.1, dy: 0.0 },
  { symbol: 'SMGR', name: 'Semen Indonesia Tbk', sector: 'Materials', market_cap: 42_000_000_000_000, price: 7100, change: 0.28, pe: 14.5, pb: 1.5, roe: 10.5, dy: 3.8 },
  { symbol: 'CPIN', name: 'Charoen Pokphand Indonesia', sector: 'Consumer Staples', market_cap: 68_000_000_000_000, price: 4150, change: 1.46, pe: 16.8, pb: 4.2, roe: 24.8, dy: 1.8 },
  { symbol: 'PGAS', name: 'Perusahaan Gas Negara Tbk', sector: 'Utilities', market_cap: 35_000_000_000_000, price: 1445, change: -0.35, pe: 8.2, pb: 1.1, roe: 13.4, dy: 6.5 },
  { symbol: 'ERAA', name: 'Erajaya Swasembada Tbk', sector: 'Consumer Discretionary', market_cap: 15_000_000_000_000, price: 480, change: 2.13, pe: 9.5, pb: 1.8, roe: 19.0, dy: 3.2 },
  { symbol: 'MAPI', name: 'Mitra Adiperkasa Tbk', sector: 'Consumer Discretionary', market_cap: 28_000_000_000_000, price: 1675, change: -0.59, pe: 14.2, pb: 3.5, roe: 24.8, dy: 1.2 },
  { symbol: 'TOWR', name: 'Sarana Menara Nusantara Tbk', sector: 'Communication Services', market_cap: 55_000_000_000_000, price: 1080, change: 0.47, pe: 20.1, pb: 5.2, roe: 25.8, dy: 1.5 },
  { symbol: 'BRPT', name: 'Barito Pacific Tbk', sector: 'Materials', market_cap: 48_000_000_000_000, price: 920, change: -2.13, pe: 30.5, pb: 1.8, roe: 5.9, dy: 0.0 },
  { symbol: 'EMTK', name: 'Elang Mahkota Teknologi', sector: 'Communication Services', market_cap: 32_000_000_000_000, price: 5525, change: 1.84, pe: 15.2, pb: 1.5, roe: 9.8, dy: 0.5 },
  { symbol: 'ACES', name: 'Ace Hardware Indonesia Tbk', sector: 'Consumer Discretionary', market_cap: 18_000_000_000_000, price: 1050, change: 0.96, pe: 25.8, pb: 4.5, roe: 17.4, dy: 2.0 },
  { symbol: 'JPFA', name: 'Japfa Comfeed Indonesia', sector: 'Consumer Staples', market_cap: 12_000_000_000_000, price: 1100, change: -1.35, pe: 8.5, pb: 1.2, roe: 14.1, dy: 3.5 },
];

export const mockInstruments: InstrumentResponse[] = stockData.map((s) => ({
  symbol: s.symbol,
  name: s.name,
  exchange: 'IDX',
  sector: s.sector,
  industry: null,
  market_cap: s.market_cap,
  is_lq45: ['BBCA', 'BBRI', 'TLKM', 'ASII', 'BMRI', 'UNVR', 'BBNI', 'BRIS', 'ADRO', 'ITMG', 'PTBA', 'ANTM', 'INCO', 'MDKA', 'KLBF', 'ICBP', 'INDF', 'HMSP', 'GGRM', 'EXCL', 'SMGR', 'CPIN', 'PGAS', 'TOWR', 'BRPT', 'EMTK', 'ERAA', 'MAPI', 'ACES', 'JPFA'].includes(s.symbol),
  board: 'Main',
}));

export const mockScreenerResults: ScreenerResult[] = stockData.map((s) => ({
  symbol: s.symbol,
  name: s.name,
  sector: s.sector,
  last_price: s.price,
  change_pct: s.change,
  volume: Math.floor(10_000_000 + Math.random() * 100_000_000),
  market_cap: s.market_cap,
  pe_ratio: s.pe,
  pbv_ratio: s.pb,
  roe: s.roe,
  dividend_yield: s.dy,
  is_lq45: mockInstruments.find((i) => i.symbol === s.symbol)?.is_lq45 ?? false,
}));

export const mockTickerData = [
  { symbol: 'IHSG', price: 7245.32, change_pct: 0.59 },
  { symbol: 'BBCA', price: 9875, change_pct: 1.25 },
  { symbol: 'BBRI', price: 5525, change_pct: -0.45 },
  { symbol: 'TLKM', price: 3840, change_pct: 0.79 },
  { symbol: 'ASII', price: 6925, change_pct: -1.12 },
  { symbol: 'BMRI', price: 6975, change_pct: 0.87 },
  { symbol: 'UNVR', price: 3800, change_pct: -2.31 },
  { symbol: 'BBNI', price: 4850, change_pct: 1.46 },
  { symbol: 'BRIS', price: 2560, change_pct: 2.40 },
];
