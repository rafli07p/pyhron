import { NextResponse } from 'next/server';

const FRED_KEY = 'f0c24db3f807b6c8a2ac1a8cad7ebad3';
const BASE = 'https://api.stlouisfed.org/fred/series/observations';

const SERIES = [
  { id: 'INTDSRIDM193N', name: 'BI Rate', unit: '%', decimals: 2, forecast: '5.75' },
  { id: 'IDNCPIALLMINMEI', name: 'Indonesia CPI', unit: '', decimals: 1, forecast: '134.2' },
  { id: 'FEDFUNDS', name: 'Fed Funds Rate', unit: '%', decimals: 2, forecast: '4.50' },
  { id: 'CHNLPRLR', name: 'China LPR', unit: '%', decimals: 2, forecast: '3.10' },
];

const STATIC_ROWS = [
  { indicator: 'Indonesia GDP', unit: '%', current: '5.11', previous: '5.05', forecast: '5.08', date: 'Q4 2025' },
  { indicator: 'USD/IDR', unit: '', current: '15,380', previous: '15,420', forecast: '15,450', date: '2026-04' },
];

async function fetchSeries(seriesId: string): Promise<{ date: string; value: string }[]> {
  try {
    const url = `${BASE}?series_id=${seriesId}&api_key=${FRED_KEY}&file_type=json&sort_order=desc&limit=5`;
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

function fmtVal(raw: string, decimals: number): string {
  const n = parseFloat(raw);
  if (isNaN(n)) return '\u2014';
  return n.toFixed(decimals);
}

function fmtDate(iso: string): string {
  if (!iso) return '';
  const [y, m] = iso.split('-');
  const months = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  return `${months[parseInt(m, 10)] ?? m} ${y}`;
}

export async function GET() {
  const fredResults = await Promise.all(
    SERIES.map(async (s) => {
      const obs = await fetchSeries(s.id);
      const current = obs[0];
      const previous = obs[1];
      return {
        indicator: s.name,
        unit: s.unit,
        current: current ? fmtVal(current.value, s.decimals) : '\u2014',
        previous: previous ? fmtVal(previous.value, s.decimals) : '\u2014',
        forecast: s.forecast,
        date: current ? fmtDate(current.date) : '',
      };
    }),
  );

  const results = [...fredResults, ...STATIC_ROWS];

  return NextResponse.json(results, {
    headers: { 'Cache-Control': 'public, s-maxage=3600, stale-while-revalidate=7200' },
  });
}
