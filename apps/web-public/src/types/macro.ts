export interface MacroIndicator {
  code: string;
  name: string;
  latest_value: number;
  unit: string;
  period: string;
  source: string;
  updated_at: string;
}

export interface IndicatorDataPoint {
  period: string;
  value: number;
  date: string;
}

export interface IndicatorHistory {
  code: string;
  name: string;
  unit: string;
  data_points: IndicatorDataPoint[];
}

export interface YieldCurvePoint {
  tenor: string;
  yield_pct: number;
  change_bps: number | null;
}

export interface PolicyEvent {
  event_date: string;
  event_type: string;
  title: string;
  description: string | null;
  previous_value: string | null;
  consensus: string | null;
  actual: string | null;
}
