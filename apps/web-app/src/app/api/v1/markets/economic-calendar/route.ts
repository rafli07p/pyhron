import { NextResponse } from 'next/server';

type Event = {
  date: string;
  indicator: string;
  unit: string;
  previous: string;
  forecast: string;
  current: string;
  released: boolean;
};

function buildSchedule(today: Date): Event[] {
  const year = today.getUTCFullYear();
  const month = today.getUTCMonth();
  const day = today.getUTCDate();

  const fmt = (offset: number): { date: string; released: boolean; iso: Date } => {
    const d = new Date(Date.UTC(year, month, day + offset));
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return {
      date: `${months[d.getUTCMonth()]} ${d.getUTCDate()}`,
      released: offset <= 0,
      iso: d,
    };
  };

  const schedule = [
    { offset: -2, indicator: 'BI Rate Decision', unit: '%', previous: '5.75', forecast: '5.75', current: '5.75' },
    { offset: 2, indicator: 'Trade Balance', unit: '', previous: '3.45B', forecast: '3.20B', current: '\u2014' },
    { offset: 4, indicator: 'China LPR (1Y)', unit: '%', previous: '3.10', forecast: '3.10', current: '\u2014' },
    { offset: 5, indicator: 'Consumer Confidence', unit: '', previous: '125.6', forecast: '126.5', current: '\u2014' },
    { offset: 7, indicator: 'Foreign Reserves', unit: '', previous: '157.1B', forecast: '158.0B', current: '\u2014' },
    { offset: 12, indicator: 'Fed Funds Rate', unit: '%', previous: '4.50', forecast: '4.50', current: '\u2014' },
  ];

  return schedule.map((s) => {
    const f = fmt(s.offset);
    return {
      date: f.date,
      indicator: s.indicator,
      unit: s.unit,
      previous: s.previous,
      forecast: s.forecast,
      current: s.current,
      released: f.released,
    };
  });
}

export async function GET() {
  const events = buildSchedule(new Date());
  return NextResponse.json(events, {
    headers: { 'Cache-Control': 'public, s-maxage=3600, stale-while-revalidate=7200' },
  });
}
