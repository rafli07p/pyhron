export interface GovernmentBond {
  series: string;
  bond_type: string;
  coupon_rate: number;
  maturity_date: string;
  yield_to_maturity: number;
  price: number;
  duration: number | null;
  outstanding: number | null;
}

export interface CorporateBond {
  series: string;
  issuer: string;
  issuer_symbol: string | null;
  rating: string;
  coupon_rate: number;
  maturity_date: string;
  yield_to_maturity: number;
  price: number;
}

export interface CreditSpread {
  rating: string;
  tenor: string;
  spread_bps: number;
  change_bps: number | null;
  benchmark_yield: number;
}
