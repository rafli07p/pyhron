'use client';

import { useCallback, useEffect, useState } from 'react';
import { useSession } from 'next-auth/react';
import { RefreshCw, TrendingDown, TrendingUp } from 'lucide-react';

// ── Types ─────────────────────────────────────────────────────────────────────
// Matches backend IndexQuote serialization (camelCase via alias).
interface IndexQuote {
  symbol: string;
  name: string;
  current: number;
  change: number;
  changePct: number;
  points: number[];
  lastUpdate: string;
}

interface ScreenerResult {
  symbol: string;
  name: string;
  sector: string | null;
  last_price: number | string;
  change_pct: number;
  volume: number;
  market_cap: number | string | null;
  pe_ratio: number | null;
  pbv_ratio: number | null;
  roe: number | null;
  dividend_yield: number | null;
  is_lq45: boolean;
}

interface ScreenerResponse {
  meta: { total_matches: number; sort_by: string; limit: number };
  results: ScreenerResult[];
}

// ── Formatters ────────────────────────────────────────────────────────────────
function safeNum(v: unknown): number | null {
  if (v === null || v === undefined) return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

function fmtIdx(v: number | null): string {
  if (v === null) return '—';
  return v.toLocaleString('id-ID', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function fmtPct(v: number | null): string {
  if (v === null) return '—';
  return (v >= 0 ? '+' : '') + v.toFixed(2) + '%';
}

function fmtPrice(v: unknown): string {
  const n = safeNum(v);
  return n !== null ? n.toLocaleString('id-ID') : '—';
}

function fmtMktCap(v: unknown): string {
  const n = safeNum(v);
  if (n === null) return '—';
  if (n >= 1e12) return (n / 1e12).toFixed(1) + 'T';
  if (n >= 1e9) return (n / 1e9).toFixed(1) + 'B';
  return n.toLocaleString('id-ID');
}

function fmtVol(v: number): string {
  if (v >= 1e9) return (v / 1e9).toFixed(1) + 'B';
  if (v >= 1e6) return (v / 1e6).toFixed(1) + 'M';
  if (v >= 1e3) return (v / 1e3).toFixed(0) + 'K';
  return v.toString();
}

// ── Components ────────────────────────────────────────────────────────────────
function IndexCard({ idx }: { idx: IndexQuote }) {
  const pos = idx.changePct >= 0;
  return (
    <div style={{
      background: '#fff', border: '1px solid var(--color-border)',
      borderRadius: 8, padding: '14px 16px',
      borderLeft: `3px solid ${pos ? 'var(--color-positive)' : 'var(--color-negative)'}`,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
        <div>
          <p style={{
            fontSize: 10, fontWeight: 700, textTransform: 'uppercase',
            letterSpacing: '0.08em', color: 'var(--color-text-muted)', marginBottom: 2,
          }}>
            {idx.symbol}
          </p>
          <p style={{ fontSize: 11, color: 'var(--color-text-secondary)', margin: 0 }}>
            {idx.name}
          </p>
        </div>
        {pos
          ? <TrendingUp size={16} style={{ color: 'var(--color-positive)' }} />
          : <TrendingDown size={16} style={{ color: 'var(--color-negative)' }} />}
      </div>
      <p style={{ fontSize: 22, fontWeight: 700, color: 'var(--color-text-primary)', margin: '0 0 4px' }}>
        {fmtIdx(idx.current)}
      </p>
      <p style={{
        fontSize: 13, fontWeight: 600, margin: 0,
        color: pos ? 'var(--color-positive)' : 'var(--color-negative)',
      }}>
        {fmtPct(idx.changePct)}
        <span style={{ fontWeight: 400, marginLeft: 6, fontSize: 12 }}>
          ({idx.change >= 0 ? '+' : ''}{fmtIdx(idx.change)}%)
        </span>
      </p>
      {idx.lastUpdate && (
        <p style={{ fontSize: 11, color: 'var(--color-text-muted)', marginTop: 4 }}>
          Updated {idx.lastUpdate} WIB
        </p>
      )}
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────
const SORT_OPTIONS = [
  { value: 'change_pct_desc', label: '↑ Gainer', backend: 'change_pct', reverse: false },
  { value: 'change_pct_asc',  label: '↓ Loser',  backend: 'change_pct', reverse: true  },
  { value: 'volume_desc',     label: 'Volume',   backend: 'volume',     reverse: false },
  { value: 'market_cap_desc', label: 'Mkt Cap',  backend: 'market_cap', reverse: false },
] as const;

type SortValue = typeof SORT_OPTIONS[number]['value'];

export default function MarketsPage() {
  const { data: session } = useSession();
  const [indices, setIndices] = useState<IndexQuote[]>([]);
  const [screener, setScreener] = useState<ScreenerResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [sortBy, setSortBy] = useState<SortValue>('change_pct_desc');
  const [sectorFilter, setSectorFilter] = useState<string>('');
  const [lq45Only, setLq45Only] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const fetchAll = useCallback(async (isRefresh = false) => {
    const token = (session as { accessToken?: string } | null)?.accessToken;
    if (!token) return;
    if (isRefresh) setRefreshing(true);
    else setLoading(true);

    const sortOpt = SORT_OPTIONS.find(o => o.value === sortBy) ?? SORT_OPTIONS[0]!;

    try {
      const params = new URLSearchParams({
        sort_by: sortOpt.backend,
        limit: '50',
        ...(sectorFilter ? { sector: sectorFilter } : {}),
        ...(lq45Only ? { lq45_only: 'true' } : {}),
      });
      const headers = { Authorization: `Bearer ${token}` };
      const [idxRes, scrRes] = await Promise.all([
        fetch('/api/v1/markets/indices', { headers }),
        fetch(`/api/v1/screener/screen?${params}`, { headers }),
      ]);
      if (idxRes.ok) setIndices(await idxRes.json());
      if (scrRes.ok) {
        const data: ScreenerResponse = await scrRes.json();
        const rows = Array.isArray(data.results) ? data.results : [];
        setScreener(sortOpt.reverse ? [...rows].reverse() : rows);
      }
    } catch {
      /* noop */
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [session, sortBy, sectorFilter, lq45Only]);

  useEffect(() => {
    void fetchAll();
  }, [fetchAll]);

  // Gainers / losers derived from current screener payload.
  const sortedByPct = [...screener].sort((a, b) => b.change_pct - a.change_pct);
  const gainers = sortedByPct.slice(0, 5);
  const losers = [...sortedByPct].reverse().slice(0, 5);

  const sectors = Array.from(new Set(screener.map(r => r.sector).filter(Boolean))) as string[];

  return (
    <div style={{ padding: '24px 28px', display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: 2 }}>
            Markets
          </h1>
          <p style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>
            IDX Market Overview — Real-time via Yahoo Finance
          </p>
        </div>
        <button
          type="button"
          onClick={() => void fetchAll(true)}
          disabled={refreshing}
          style={{
            display: 'flex', alignItems: 'center', gap: 6,
            padding: '6px 14px', borderRadius: 6, fontSize: 12, fontWeight: 600,
            background: 'var(--color-blue-primary)', color: 'white',
            border: 'none', cursor: 'pointer', opacity: refreshing ? 0.7 : 1,
          }}
        >
          <RefreshCw size={13} className={refreshing ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {/* Index cards */}
      {indices.length > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 10 }}>
          {indices.map(idx => <IndexCard key={idx.symbol} idx={idx} />)}
        </div>
      )}

      {/* Top movers */}
      {screener.length > 0 && (
        <div style={{
          background: '#fff', border: '1px solid var(--color-border)',
          borderRadius: 8, padding: '14px 16px',
        }}>
          <p style={{
            fontSize: 10, fontWeight: 700, textTransform: 'uppercase',
            letterSpacing: '0.08em', color: 'var(--color-text-muted)', marginBottom: 12,
          }}>
            Top Movers — Today
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <div>
              <p style={{ fontSize: 11, fontWeight: 600, color: 'var(--color-positive)', marginBottom: 8 }}>
                ▲ Top Gainers
              </p>
              {gainers.map(r => (
                <div
                  key={r.symbol}
                  style={{
                    display: 'flex', justifyContent: 'space-between',
                    alignItems: 'center', padding: '5px 0',
                    borderBottom: '1px solid var(--color-border-subtle)',
                  }}
                >
                  <div>
                    <span style={{
                      fontSize: 12, fontWeight: 700, color: 'var(--color-blue-primary)',
                      fontFamily: 'monospace', marginRight: 8,
                    }}>
                      {r.symbol}
                    </span>
                    <span style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>
                      {fmtPrice(r.last_price)}
                    </span>
                  </div>
                  <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-positive)' }}>
                    +{r.change_pct.toFixed(2)}%
                  </span>
                </div>
              ))}
            </div>
            <div>
              <p style={{ fontSize: 11, fontWeight: 600, color: 'var(--color-negative)', marginBottom: 8 }}>
                ▼ Top Losers
              </p>
              {losers.map(r => (
                <div
                  key={r.symbol}
                  style={{
                    display: 'flex', justifyContent: 'space-between',
                    alignItems: 'center', padding: '5px 0',
                    borderBottom: '1px solid var(--color-border-subtle)',
                  }}
                >
                  <div>
                    <span style={{
                      fontSize: 12, fontWeight: 700, color: 'var(--color-blue-primary)',
                      fontFamily: 'monospace', marginRight: 8,
                    }}>
                      {r.symbol}
                    </span>
                    <span style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>
                      {fmtPrice(r.last_price)}
                    </span>
                  </div>
                  <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-negative)' }}>
                    {r.change_pct.toFixed(2)}%
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Screener table */}
      <div style={{ background: '#fff', border: '1px solid var(--color-border)', borderRadius: 8, overflow: 'hidden' }}>
        <div style={{
          padding: '10px 14px', borderBottom: '1px solid var(--color-border)',
          display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap',
        }}>
          <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--color-text-primary)' }}>
            IDX Screener
          </span>
          <span style={{ fontSize: 11, color: 'var(--color-text-muted)', marginRight: 4 }}>Sort:</span>
          <div style={{ display: 'flex', gap: 4 }}>
            {SORT_OPTIONS.map(opt => (
              <button
                key={opt.value}
                type="button"
                onClick={() => setSortBy(opt.value)}
                style={{
                  padding: '3px 10px', fontSize: 11, borderRadius: 4,
                  border: '1px solid var(--color-border)',
                  background: sortBy === opt.value ? 'var(--color-blue-primary)' : 'white',
                  color: sortBy === opt.value ? 'white' : 'var(--color-text-secondary)',
                  cursor: 'pointer', fontWeight: sortBy === opt.value ? 600 : 400,
                }}
              >
                {opt.label}
              </button>
            ))}
          </div>
          <label style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 12, cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={lq45Only}
              onChange={e => setLq45Only(e.target.checked)}
              style={{ cursor: 'pointer' }}
            />
            LQ45 only
          </label>
          {sectors.length > 0 && (
            <select
              value={sectorFilter}
              onChange={e => setSectorFilter(e.target.value)}
              style={{
                fontSize: 12, padding: '3px 8px', borderRadius: 4,
                border: '1px solid var(--color-border)',
                background: 'var(--color-bg-card)', color: 'var(--color-text-primary)',
              }}
            >
              <option value="">All sectors</option>
              {sectors.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          )}
          <span style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--color-text-muted)' }}>
            {screener.length} stocks
          </span>
        </div>

        {loading ? (
          <div style={{ padding: 60, textAlign: 'center', color: 'var(--color-text-muted)', fontSize: 13 }}>
            Loading market data…
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ background: 'var(--color-bg-page)', borderBottom: '1px solid var(--color-border)' }}>
                  {['Symbol', 'Company', 'Sector', 'Price (IDR)', 'Change %', 'Volume', 'Mkt Cap', 'P/E', 'P/BV', 'ROE', 'Div Yield', 'LQ45'].map(h => (
                    <th key={h} style={{
                      padding: '9px 12px',
                      textAlign: h === 'Symbol' || h === 'Company' || h === 'Sector' ? 'left' : 'right',
                      fontSize: 10, fontWeight: 700, letterSpacing: '0.06em',
                      textTransform: 'uppercase', color: 'var(--color-text-muted)',
                      whiteSpace: 'nowrap',
                    }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {screener.map((r, i) => {
                  const pos = r.change_pct >= 0;
                  const roe = r.roe !== null ? r.roe * 100 : null;
                  const dy = r.dividend_yield !== null ? r.dividend_yield * 100 : null;
                  return (
                    <tr key={r.symbol} style={{
                      borderBottom: '1px solid var(--color-border-subtle)',
                      background: i % 2 === 0 ? 'transparent' : 'rgba(0,0,0,0.01)',
                    }}>
                      <td style={{
                        padding: '9px 12px', fontWeight: 700,
                        color: 'var(--color-blue-primary)', fontFamily: 'monospace', whiteSpace: 'nowrap',
                      }}>
                        {r.symbol}
                        {r.is_lq45 && (
                          <span style={{
                            marginLeft: 5, fontSize: 9, padding: '1px 4px', borderRadius: 2,
                            background: 'rgba(0,87,168,0.1)', color: 'var(--color-blue-primary)',
                          }}>LQ45</span>
                        )}
                      </td>
                      <td style={{
                        padding: '9px 12px', color: 'var(--color-text-secondary)',
                        maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                      }}>
                        {r.name}
                      </td>
                      <td style={{ padding: '9px 12px', color: 'var(--color-text-muted)', fontSize: 11 }}>
                        {r.sector ?? '—'}
                      </td>
                      <td style={{
                        padding: '9px 12px', textAlign: 'right', fontWeight: 600,
                        color: 'var(--color-text-primary)',
                      }}>
                        {fmtPrice(r.last_price)}
                      </td>
                      <td style={{
                        padding: '9px 12px', textAlign: 'right', fontWeight: 600,
                        color: pos ? 'var(--color-positive)' : 'var(--color-negative)',
                      }}>
                        {fmtPct(r.change_pct)}
                      </td>
                      <td style={{ padding: '9px 12px', textAlign: 'right', color: 'var(--color-text-secondary)' }}>
                        {fmtVol(r.volume)}
                      </td>
                      <td style={{ padding: '9px 12px', textAlign: 'right', color: 'var(--color-text-secondary)' }}>
                        {fmtMktCap(r.market_cap)}
                      </td>
                      <td style={{ padding: '9px 12px', textAlign: 'right', color: 'var(--color-text-secondary)' }}>
                        {r.pe_ratio !== null ? r.pe_ratio.toFixed(1) + 'x' : '—'}
                      </td>
                      <td style={{ padding: '9px 12px', textAlign: 'right', color: 'var(--color-text-secondary)' }}>
                        {r.pbv_ratio !== null ? r.pbv_ratio.toFixed(2) + 'x' : '—'}
                      </td>
                      <td style={{ padding: '9px 12px', textAlign: 'right', color: 'var(--color-text-secondary)' }}>
                        {roe !== null ? roe.toFixed(1) + '%' : '—'}
                      </td>
                      <td style={{ padding: '9px 12px', textAlign: 'right', color: 'var(--color-text-secondary)' }}>
                        {dy !== null ? dy.toFixed(2) + '%' : '—'}
                      </td>
                      <td style={{ padding: '9px 12px', textAlign: 'center' }}>
                        {r.is_lq45 ? '✓' : ''}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
