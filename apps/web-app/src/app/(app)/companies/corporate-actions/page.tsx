'use client';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useSession } from 'next-auth/react';
import { useCompanyStore } from '@/stores/company';
import { CompanySelector } from '@/components/companies/CompanySelector';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine,
} from 'recharts';

// ── Types ──────────────────────────────────────────────────────────────────────
interface CorporateAction {
  symbol: string;
  action_type: string;
  ex_date: string;
  record_date: string | null;
  description: string;
  value: number | string | null;
}

interface PriceBar {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface PriceImpact {
  action: CorporateAction;
  priceT0: number | null;       // close on ex_date or nearest
  priceTMinus30: number | null; // close ~30 days before
  priceTPlus30: number | null;  // close ~30 days after
  returnBefore: number | null;  // % return T-30 → T0
  returnAfter: number | null;   // % return T0 → T+30
  divYield: number | null;      // value / priceT0
  window: PriceBar[];           // 60-day window for chart
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function daysBetween(a: string, b: string): number {
  return Math.round((new Date(b).getTime() - new Date(a).getTime()) / 86400000);
}

function isoDate(d: Date): string {
  const parts = d.toISOString().split('T');
  return parts[0] ?? '';
}

function nearestBar(bars: PriceBar[], targetDate: string): PriceBar | null {
  if (!bars.length) return null;
  let best: PriceBar | null = null;
  let bestDiff = Infinity;
  for (const b of bars) {
    const d = Math.abs(daysBetween(b.date, targetDate));
    if (d < bestDiff) { bestDiff = d; best = b; }
  }
  return bestDiff <= 14 ? best : null; // max 14 days gap
}

function computeImpact(action: CorporateAction, bars: PriceBar[]): PriceImpact {
  const exDate = action.ex_date;
  const sorted = [...bars].sort((a, b) => a.date.localeCompare(b.date));

  // T-30, T0, T+30 using calendar days, mapped to nearest weekly bar
  const t0 = nearestBar(sorted, exDate);
  const targetMinus30 = new Date(exDate);
  targetMinus30.setDate(targetMinus30.getDate() - 30);
  const tMinus30 = nearestBar(sorted, isoDate(targetMinus30));
  const targetPlus30 = new Date(exDate);
  targetPlus30.setDate(targetPlus30.getDate() + 30);
  const tPlus30 = nearestBar(sorted, isoDate(targetPlus30));

  const priceT0 = t0?.close ?? null;
  const priceTMinus30 = tMinus30?.close ?? null;
  const priceTPlus30 = tPlus30?.close ?? null;

  const returnBefore = priceT0 !== null && priceTMinus30 !== null && priceTMinus30 !== 0
    ? ((priceT0 - priceTMinus30) / priceTMinus30) * 100 : null;
  const returnAfter = priceTPlus30 !== null && priceT0 !== null && priceT0 !== 0
    ? ((priceTPlus30 - priceT0) / priceT0) * 100 : null;
  const divYield = action.action_type === 'dividend' && priceT0 !== null && priceT0 !== 0 && action.value !== null
    ? (Number(action.value) / priceT0) * 100 : null;

  // 60-day window: T-30 to T+30
  const windowStart = new Date(exDate);
  windowStart.setDate(windowStart.getDate() - 35);
  const windowEnd = new Date(exDate);
  windowEnd.setDate(windowEnd.getDate() + 35);
  const ws = isoDate(windowStart);
  const we = isoDate(windowEnd);
  const window = sorted.filter(b => b.date >= ws && b.date <= we);

  return { action, priceT0, priceTMinus30, priceTPlus30, returnBefore, returnAfter, divYield, window };
}

// ── Formatters ─────────────────────────────────────────────────────────────────
function fmtPct(v: number | null, decimals = 2): string {
  if (v === null || v === undefined) return '—';
  return (v >= 0 ? '+' : '') + v.toFixed(decimals) + '%';
}
function fmtIDR(v: number | string | null): string {
  if (v === null || v === undefined) return '—';
  const n = Number(v);
  if (!isFinite(n)) return '—';
  return 'IDR ' + n.toLocaleString('id-ID', { maximumFractionDigits: 0 });
}
function fmtPrice(v: number | null): string {
  if (v === null) return '—';
  return v.toLocaleString('id-ID', { maximumFractionDigits: 0 });
}
function fmtDate(d: string): string {
  return new Date(d).toLocaleDateString('id-ID', { day: '2-digit', month: 'short', year: 'numeric' });
}

// ── Badge ──────────────────────────────────────────────────────────────────────
const BADGE: Record<string, { bg: string; fg: string; label: string }> = {
  dividend:    { bg: 'rgba(0,87,168,0.10)',  fg: '#0057A8', label: 'Dividend' },
  stock_split: { bg: 'rgba(217,119,6,0.10)', fg: '#b45309', label: 'Stock Split' },
  rights_issue:{ bg: 'rgba(5,122,85,0.10)',  fg: '#057a55', label: 'Rights Issue' },
};
function ActionBadge({ type }: { type: string }) {
  const b = BADGE[type] ?? { bg: 'rgba(107,114,128,0.10)', fg: '#6b7280', label: type };
  return (
    <span style={{
      padding: '2px 8px', borderRadius: 4, fontSize: 10, fontWeight: 700,
      textTransform: 'uppercase', letterSpacing: '0.06em',
      background: b.bg, color: b.fg,
    }}>{b.label}</span>
  );
}

// ── Impact Mini Chart ──────────────────────────────────────────────────────────
function ImpactChart({ impact }: { impact: PriceImpact }) {
  if (!impact.window.length) {
    return <div style={{ height: 80, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--color-text-muted)', fontSize: 11 }}>No price data in window</div>;
  }
  const data = impact.window.map(b => ({ date: b.date.slice(5), price: b.close }));
  const exDateShort = impact.action.ex_date.slice(5);
  const minP = Math.min(...data.map(d => d.price)) * 0.995;
  const maxP = Math.max(...data.map(d => d.price)) * 1.005;
  return (
    <ResponsiveContainer width="100%" height={80}>
      <AreaChart data={data} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="priceGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#0057A8" stopOpacity={0.15} />
            <stop offset="95%" stopColor="#0057A8" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" />
        <XAxis dataKey="date" tick={{ fontSize: 9 }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
        <YAxis domain={[minP, maxP]} tick={{ fontSize: 9 }} tickLine={false} axisLine={false} width={50}
          tickFormatter={v => (Number(v) / 1000).toFixed(1) + 'K'} />
        <Tooltip
          contentStyle={{ fontSize: 11, borderRadius: 6, border: '1px solid var(--color-border)' }}
          formatter={(v) => ['IDR ' + Number(v).toLocaleString('id-ID'), 'Close']}
        />
        <ReferenceLine x={exDateShort} stroke="#dc2626" strokeDasharray="4 2" strokeWidth={1.5}
          label={{ value: 'Ex-Date', position: 'top', fontSize: 9, fill: '#dc2626' }} />
        <Area type="monotone" dataKey="price" stroke="#0057A8" strokeWidth={1.5}
          fill="url(#priceGrad)" dot={false} />
      </AreaChart>
    </ResponsiveContainer>
  );
}

// ── Impact Row ────────────────────────────────────────────────────────────────
type DetailRow = { label: string; value: string; colored?: number | null };

function ImpactRow({ impact, expanded, onToggle }: {
  impact: PriceImpact;
  expanded: boolean;
  onToggle: () => void;
}) {
  const a = impact.action;
  const afterPos = impact.returnAfter !== null ? impact.returnAfter >= 0 : undefined;
  const beforePos = impact.returnBefore !== null ? impact.returnBefore >= 0 : undefined;

  const details: DetailRow[] = [
    { label: 'T−30 Price', value: fmtPrice(impact.priceTMinus30) },
    { label: 'T0 Price (Ex-Date)', value: fmtPrice(impact.priceT0) },
    { label: 'T+30 Price', value: fmtPrice(impact.priceTPlus30) },
    { label: 'Pre-event Return', value: fmtPct(impact.returnBefore), colored: impact.returnBefore },
    { label: 'Post-event Return', value: fmtPct(impact.returnAfter), colored: impact.returnAfter },
    ...(impact.divYield !== null
      ? [{ label: 'Dividend Yield', value: `${impact.divYield.toFixed(2)}%` } as DetailRow]
      : []),
  ];

  return (
    <div style={{ borderBottom: '1px solid var(--color-border-subtle)' }}>
      {/* Summary row */}
      <div
        onClick={onToggle}
        style={{
          display: 'grid',
          gridTemplateColumns: '100px 110px 140px 90px 90px 90px 90px 90px 1fr',
          alignItems: 'center',
          padding: '10px 16px',
          cursor: 'pointer',
          gap: 8,
          transition: 'background 0.1s',
        }}
        onMouseEnter={e => (e.currentTarget.style.background = 'rgba(0,87,168,0.03)')}
        onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
      >
        <div><ActionBadge type={a.action_type} /></div>
        <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-text-primary)', fontFamily: 'monospace' }}>
          {fmtDate(a.ex_date)}
        </div>
        <div style={{ fontSize: 11, color: 'var(--color-text-secondary)' }}>{a.description}</div>
        <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--color-text-primary)', textAlign: 'right' }}>
          {fmtIDR(a.value)}
        </div>
        <div style={{ fontSize: 12, fontWeight: 600, textAlign: 'right', color: 'var(--color-text-secondary)' }}>
          {impact.priceTMinus30 !== null ? fmtPrice(impact.priceTMinus30) : '—'}
        </div>
        <div style={{ fontSize: 12, fontWeight: 700, textAlign: 'right', color: 'var(--color-text-primary)' }}>
          {impact.priceT0 !== null ? fmtPrice(impact.priceT0) : '—'}
        </div>
        <div style={{ fontSize: 12, fontWeight: 700, textAlign: 'right',
          color: beforePos === undefined ? 'var(--color-text-muted)' : beforePos ? 'var(--color-positive)' : 'var(--color-negative)' }}>
          {fmtPct(impact.returnBefore)}
        </div>
        <div style={{ fontSize: 12, fontWeight: 700, textAlign: 'right',
          color: afterPos === undefined ? 'var(--color-text-muted)' : afterPos ? 'var(--color-positive)' : 'var(--color-negative)' }}>
          {fmtPct(impact.returnAfter)}
        </div>
        <div style={{ fontSize: 11, textAlign: 'right', color: 'var(--color-text-muted)' }}>
          {impact.divYield !== null ? `${impact.divYield.toFixed(2)}% yield` : ''}
        </div>
      </div>

      {/* Expanded: price impact chart */}
      {expanded && (
        <div style={{ padding: '0 16px 16px', background: 'rgba(0,87,168,0.02)' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 200px', gap: 20, alignItems: 'start' }}>
            <div>
              <p style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.07em', color: 'var(--color-text-muted)', marginBottom: 8 }}>
                Price Impact: 30 Days Before &amp; After Ex-Date
              </p>
              <ImpactChart impact={impact} />
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, paddingTop: 24 }}>
              {details.map(({ label, value, colored }) => {
                const hasColor = colored !== undefined && colored !== null;
                return (
                  <div key={label} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>{label}</span>
                    <span style={{
                      fontSize: 12, fontWeight: 700,
                      color: hasColor
                        ? (colored >= 0 ? 'var(--color-positive)' : 'var(--color-negative)')
                        : 'var(--color-text-primary)',
                    }}>{value}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Aggregate KPIs ────────────────────────────────────────────────────────────
function AggregateKPIs({ impacts }: { impacts: PriceImpact[] }) {
  const divImpacts = impacts.filter(i => i.action.action_type === 'dividend' && i.returnAfter !== null);
  const avgPostReturn = divImpacts.length
    ? divImpacts.reduce((s, i) => s + (i.returnAfter ?? 0), 0) / divImpacts.length : null;
  const totalDivPaid = impacts
    .filter(i => i.action.action_type === 'dividend')
    .reduce((s, i) => s + Number(i.action.value ?? 0), 0);
  const splitEvents = impacts.filter(i => i.action.action_type === 'stock_split');
  const yieldImpacts = divImpacts.filter(i => i.divYield !== null);
  const avgDivYield = yieldImpacts.length
    ? yieldImpacts.reduce((s, i) => s + (i.divYield ?? 0), 0) / yieldImpacts.length
    : null;

  type KpiEntry = { label: string; value: string; sub: string; positive?: boolean };
  const kpis: KpiEntry[] = [
    {
      label: 'Avg Post-Dividend Return',
      value: avgPostReturn !== null ? fmtPct(avgPostReturn) : '—',
      sub: `${divImpacts.length} dividend events analysed`,
      positive: avgPostReturn !== null ? avgPostReturn >= 0 : undefined,
    },
    {
      label: 'Total Dividends (5Y)',
      value: `IDR ${totalDivPaid.toLocaleString('id-ID')}`,
      sub: 'Cumulative per share',
    },
    {
      label: 'Avg Dividend Yield',
      value: avgDivYield !== null ? `${avgDivYield.toFixed(2)}%` : '—',
      sub: 'At ex-date price',
    },
    {
      label: 'Stock Splits',
      value: String(splitEvents.length),
      sub: splitEvents.length > 0 ? splitEvents.map(s => s.action.ex_date.slice(0, 4)).join(', ') : 'None in history',
    },
  ];

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
      {kpis.map(({ label, value, sub, positive }) => (
        <div key={label} style={{ background: '#fff', border: '1px solid var(--color-border)', borderRadius: 8, padding: '14px 18px' }}>
          <p style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--color-text-muted)', marginBottom: 6 }}>
            {label}
          </p>
          <p style={{
            fontSize: 20, fontWeight: 700, margin: '0 0 4px',
            color: positive === undefined ? 'var(--color-text-primary)' : positive ? 'var(--color-positive)' : 'var(--color-negative)',
          }}>
            {value}
          </p>
          <p style={{ fontSize: 11, color: 'var(--color-text-muted)', margin: 0 }}>{sub}</p>
        </div>
      ))}
    </div>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────────
type FilterType = 'all' | 'dividend' | 'stock_split';

export default function CorporateActionsPage() {
  const { data: session } = useSession();
  const { selectedSymbol } = useCompanyStore();
  const [actions, setActions] = useState<CorporateAction[]>([]);
  const [priceBars, setPriceBars] = useState<PriceBar[]>([]);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState<FilterType>('all');
  const [expandedRow, setExpandedRow] = useState<string | null>(null);

  const authHeader = useCallback((): Record<string, string> => {
    const token = (session as { accessToken?: string } | null)?.accessToken;
    return token ? { Authorization: `Bearer ${token}` } : {};
  }, [session]);

  useEffect(() => {
    const token = (session as { accessToken?: string } | null)?.accessToken;
    if (!token || !selectedSymbol) return;
    setLoading(true);
    setExpandedRow(null);
    Promise.all([
      fetch(`/api/v1/stocks/${selectedSymbol}/corporate-actions`, { headers: authHeader() }).then(r => r.json()),
      fetch(`/api/v1/stocks/${selectedSymbol}/price-history?period=5y`, { headers: authHeader() }).then(r => r.json()),
    ]).then(([acts, prices]) => {
      setActions(Array.isArray(acts) ? acts : []);
      setPriceBars(Array.isArray(prices) ? prices : []);
    }).catch(() => {
      setActions([]);
      setPriceBars([]);
    }).finally(() => setLoading(false));
  }, [selectedSymbol, session, authHeader]);

  const impacts = useMemo<PriceImpact[]>(() =>
    actions.map(a => computeImpact(a, priceBars)),
    [actions, priceBars]
  );

  const filtered = useMemo(() =>
    filter === 'all' ? impacts : impacts.filter(i => i.action.action_type === filter),
    [impacts, filter]
  );

  return (
    <div style={{ padding: '24px 28px', display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: 2 }}>
            Corporate Actions
          </h1>
          <p style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>
            Dividend history, stock splits, and price impact analysis · {selectedSymbol}
          </p>
        </div>
        <CompanySelector />
      </div>

      {loading ? (
        <div style={{ padding: 60, textAlign: 'center', color: 'var(--color-text-muted)', fontSize: 13 }}>
          Loading corporate actions &amp; price history…
        </div>
      ) : (
        <>
          {/* Aggregate KPIs */}
          <AggregateKPIs impacts={impacts} />

          {/* Filter pills */}
          <div style={{ display: 'flex', gap: 6 }}>
            {([
              { id: 'all', label: 'All Events' },
              { id: 'dividend', label: 'Dividends' },
              { id: 'stock_split', label: 'Stock Splits' },
            ] as const).map(f => {
              const active = filter === f.id;
              return (
                <button key={f.id} type="button" onClick={() => setFilter(f.id)} style={{
                  padding: '5px 14px', fontSize: 12, fontWeight: active ? 700 : 500, borderRadius: 20,
                  border: `1px solid ${active ? 'var(--color-blue-primary)' : 'var(--color-border)'}`,
                  background: active ? 'var(--color-blue-primary)' : '#fff',
                  color: active ? '#fff' : 'var(--color-text-secondary)', cursor: 'pointer',
                }}>
                  {f.label} {f.id !== 'all' && `(${impacts.filter(i => i.action.action_type === f.id).length})`}
                </button>
              );
            })}
          </div>

          {/* Table */}
          <div style={{ background: '#fff', border: '1px solid var(--color-border)', borderRadius: 8, overflow: 'hidden' }}>
            {/* Column headers */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: '100px 110px 140px 90px 90px 90px 90px 90px 1fr',
              padding: '8px 16px', gap: 8,
              background: 'var(--color-bg-page)',
              borderBottom: '1px solid var(--color-border)',
            }}>
              {['Type', 'Ex-Date', 'Description', 'Value', 'T−30', 'T0 Price', 'Pre-Event', 'Post-Event', 'Yield'].map(h => (
                <div key={h} style={{
                  fontSize: 10, fontWeight: 700, textTransform: 'uppercase',
                  letterSpacing: '0.06em', color: 'var(--color-text-muted)',
                  textAlign: ['Value', 'T−30', 'T0 Price', 'Pre-Event', 'Post-Event', 'Yield'].includes(h) ? 'right' : 'left',
                }}>
                  {h}
                </div>
              ))}
            </div>

            {filtered.length === 0 ? (
              <div style={{ padding: 40, textAlign: 'center', color: 'var(--color-text-muted)', fontSize: 13 }}>
                No {filter === 'all' ? 'corporate actions' : filter.replace('_', ' ')} found for {selectedSymbol}.
              </div>
            ) : (
              filtered.map(impact => {
                const key = `${impact.action.ex_date}-${impact.action.action_type}`;
                return (
                  <ImpactRow
                    key={key}
                    impact={impact}
                    expanded={expandedRow === key}
                    onToggle={() => setExpandedRow(prev => prev === key ? null : key)}
                  />
                );
              })
            )}
          </div>

          {/* Footnote */}
          <p style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>
            T−30 / T0 / T+30 prices are nearest weekly close to calendar target date (max ±14 days).
            Price history sourced from Yahoo Finance. Click any row to expand the price impact chart.
          </p>
        </>
      )}
    </div>
  );
}
