'use client';

import { useState, useEffect, useCallback } from 'react';
import { useSession } from 'next-auth/react';
import { RefreshCw, Filter } from 'lucide-react';

interface ScreenerRow {
  symbol: string;
  name: string;
  sector: string | null;
  last_price: number;
  change_pct: number;
  volume: number;
  market_cap: number | null;
  pe_ratio: number | null;
  pbv_ratio: number | null;
  roe: number | null;
  dividend_yield: number | null;
  is_lq45: boolean;
}

interface ScreenerResponse {
  meta: { total_matches: number; sort_by: string; limit: number };
  results: ScreenerRow[];
}

function fmtPrice(v: number) {
  return v > 0 ? v.toLocaleString('id-ID', { minimumFractionDigits: 0 }) : '—';
}
function fmtMktCap(v: number | null) {
  if (!v || v === 0) return '—';
  const t = v / 1e12;
  if (t >= 1) return `${t.toFixed(1)}T`;
  const b = v / 1e9;
  return `${b.toFixed(0)}B`;
}
function fmtVol(v: number) {
  if (v === 0) return '—';
  if (v >= 1e9) return (v / 1e9).toFixed(1) + 'B';
  if (v >= 1e6) return (v / 1e6).toFixed(1) + 'M';
  if (v >= 1e3) return (v / 1e3).toFixed(0) + 'K';
  return v.toString();
}

const SORT_OPTIONS = [
  { value: 'market_cap', label: 'Market Cap' },
  { value: 'pe_ratio', label: 'P/E Ratio' },
  { value: 'pbv_ratio', label: 'P/BV Ratio' },
  { value: 'roe', label: 'ROE' },
  { value: 'volume', label: 'Volume' },
];

export default function MarketsPage() {
  const [data, setData] = useState<ScreenerResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lq45Only, setLq45Only] = useState(false);
  const [sortBy, setSortBy] = useState('market_cap');
  const [refreshing, setRefreshing] = useState(false);
  const { data: session } = useSession();

  const fetchData = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        sort_by: sortBy,
        limit: '50',
        ...(lq45Only ? { lq45_only: 'true' } : {}),
      });
      const headers: Record<string, string> = {};
      const token = (session as { accessToken?: string } | null)?.accessToken;
      if (token) headers['Authorization'] = `Bearer ${token}`;

      const res = await fetch(`/api/v1/screener/screen?${params}`, { headers });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setData(json);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [sortBy, lq45Only, session]);

  useEffect(() => { fetchData(); }, [fetchData]);

  return (
    <div className="flex w-full flex-1 flex-col gap-2 p-2 md:p-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 style={{ fontSize: 16, fontWeight: 700, color: 'var(--color-text-primary)' }}>
            IDX Equity Screener
          </h1>
          <p style={{ fontSize: 12, color: 'var(--color-text-muted)', marginTop: 2 }}>
            {data ? `${data.meta.total_matches} instruments` : 'Loading…'}
          </p>
        </div>
        <button
          onClick={() => fetchData(true)}
          disabled={refreshing}
          style={{
            display: 'flex', alignItems: 'center', gap: 6,
            padding: '6px 12px', borderRadius: 6, fontSize: 12,
            background: 'var(--color-blue-primary)', color: 'white',
            border: 'none', cursor: 'pointer', fontWeight: 600,
            opacity: refreshing ? 0.7 : 1,
          }}
        >
          <RefreshCw size={13} className={refreshing ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {/* Filter Bar */}
      <div className="card-base" style={{ padding: '10px 14px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <Filter size={13} style={{ color: 'var(--color-text-muted)' }} />
            <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              Filters
            </span>
          </div>
          <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={lq45Only}
              onChange={e => setLq45Only(e.target.checked)}
              style={{ accentColor: 'var(--color-blue-primary)', width: 14, height: 14 }}
            />
            <span style={{ fontSize: 12, color: 'var(--color-text-primary)', fontWeight: 500 }}>
              LQ45 Only
            </span>
          </label>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>Sort by</span>
            <select
              value={sortBy}
              onChange={e => setSortBy(e.target.value)}
              style={{
                fontSize: 12, padding: '3px 8px', borderRadius: 4,
                border: '1px solid var(--color-border)',
                background: 'var(--color-bg-card)',
                color: 'var(--color-text-primary)',
                cursor: 'pointer',
              }}
            >
              {SORT_OPTIONS.map(o => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="card-base" style={{ padding: 0, overflow: 'hidden' }}>
        {loading ? (
          <div style={{ padding: 40, textAlign: 'center', color: 'var(--color-text-muted)', fontSize: 13 }}>
            Loading instruments…
          </div>
        ) : error ? (
          <div style={{ padding: 40, textAlign: 'center', color: 'var(--color-negative)', fontSize: 13 }}>
            Error: {error}
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--color-border)', background: 'var(--color-bg-page)' }}>
                  {['Symbol','Company','Sector','Price (IDR)','Chg%','Volume','Mkt Cap','P/E','P/BV','LQ45'].map(h => (
                    <th key={h} style={{
                      padding: '8px 12px', textAlign: h === 'Symbol' || h === 'Company' || h === 'Sector' ? 'left' : 'right',
                      fontSize: 10, fontWeight: 700, letterSpacing: '0.06em',
                      textTransform: 'uppercase', color: 'var(--color-text-muted)',
                      whiteSpace: 'nowrap',
                    }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data?.results.map((row, i) => (
                  <tr key={row.symbol} style={{
                    borderBottom: '1px solid var(--color-border-subtle)',
                    background: i % 2 === 0 ? 'transparent' : 'rgba(0,0,0,0.01)',
                  }}
                  onMouseEnter={e => (e.currentTarget.style.background = 'var(--color-bg-hover, rgba(0,87,168,0.04))')}
                  onMouseLeave={e => (e.currentTarget.style.background = i % 2 === 0 ? 'transparent' : 'rgba(0,0,0,0.01)')}
                  >
                    <td style={{ padding: '7px 12px', fontWeight: 700, color: 'var(--color-blue-primary)', fontFamily: 'var(--font-mono, monospace)', whiteSpace: 'nowrap' }}>
                      {row.symbol}
                    </td>
                    <td style={{ padding: '7px 12px', color: 'var(--color-text-primary)', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {row.name}
                    </td>
                    <td style={{ padding: '7px 12px', color: 'var(--color-text-secondary)' }}>
                      {row.sector ?? '—'}
                    </td>
                    <td style={{ padding: '7px 12px', textAlign: 'right', fontFamily: 'var(--font-mono, monospace)', fontWeight: 600, color: 'var(--color-text-primary)' }}>
                      {fmtPrice(row.last_price)}
                    </td>
                    <td style={{ padding: '7px 12px', textAlign: 'right', fontFamily: 'var(--font-mono, monospace)', fontWeight: 600,
                      color: row.change_pct > 0 ? 'var(--color-positive)' : row.change_pct < 0 ? 'var(--color-negative)' : 'var(--color-text-muted)' }}>
                      {row.change_pct > 0 ? '+' : ''}{row.change_pct.toFixed(2)}%
                    </td>
                    <td style={{ padding: '7px 12px', textAlign: 'right', color: 'var(--color-text-secondary)', fontFamily: 'var(--font-mono, monospace)' }}>
                      {fmtVol(row.volume)}
                    </td>
                    <td style={{ padding: '7px 12px', textAlign: 'right', color: 'var(--color-text-secondary)', fontFamily: 'var(--font-mono, monospace)' }}>
                      {fmtMktCap(row.market_cap)}
                    </td>
                    <td style={{ padding: '7px 12px', textAlign: 'right', color: 'var(--color-text-secondary)', fontFamily: 'var(--font-mono, monospace)' }}>
                      {row.pe_ratio ? row.pe_ratio.toFixed(1) + 'x' : '—'}
                    </td>
                    <td style={{ padding: '7px 12px', textAlign: 'right', color: 'var(--color-text-secondary)', fontFamily: 'var(--font-mono, monospace)' }}>
                      {row.pbv_ratio ? row.pbv_ratio.toFixed(2) + 'x' : '—'}
                    </td>
                    <td style={{ padding: '7px 12px', textAlign: 'center' }}>
                      {row.is_lq45 ? (
                        <span style={{
                          fontSize: 9, fontWeight: 700, padding: '2px 5px',
                          borderRadius: 3, background: 'var(--color-blue-primary)',
                          color: 'white', letterSpacing: '0.04em',
                        }}>LQ45</span>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
