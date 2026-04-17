import { NextResponse } from 'next/server';

const FRED_KEY = 'f0c24db3f807b6c8a2ac1a8cad7ebad3';
const BASE = 'https://api.stlouisfed.org/fred/series/observations';

const SERIES = [
  { id: 'IDNCPIALLMINMEI', name: 'Indonesia CPI', unit: '%' },
  { id: 'IDNGDPNQDSMEI', name: 'Indonesia GDP', unit: 'B IDR' },
  { id: 'INTDSRIDM193N', name: 'BI Interest Rate', unit: '%' },
  { id: 'DEXINUS', name: 'USD/IDR Exchange Rate', unit: '' },
  { id: 'CHNLPRLR', name: 'China Loan Prime Rate', unit: '%' },
  { id: 'FEDFUNDS', name: 'Fed Funds Rate', unit: '%' },
];

async function fetchSeries(seriesId: string): Promise<{ date: string; value: string }[]> {
  try {
    const url = `${BASE}?series_id=${seriesId}&api_key=${FRED_KEY}&file_type=json&sort_order=desc&limit=2`;
    const res = await fetch(url, { next: { revalidate: 3600 } });
    if (!res.ok) return [];
    const data = await res.json();
    return (data.observations ?? [])
      .filter((o: { value: string }) => o.value !== '.')
      .map((o: { date: string; value: string }) => ({ date: o.date, value: o.value }));
  } catch {
    return [];
  }
}

export async function GET() {
  const results = await Promise.all(
    SERIES.map(async (s) => {
      const obs = await fetchSeries(s.id);
      const current = obs[0];
      const previous = obs[1];
      return {
        indicator: s.name,
        unit: s.unit,
        current: current?.value ?? '-',
        previous: previous?.value ?? '-',
        date: current?.date ?? '',
      };
    }),
  );

  return NextResponse.json(results, {
    headers: { 'Cache-Control': 'public, s-maxage=3600, stale-while-revalidate=7200' },
  });
}
