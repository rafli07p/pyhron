'use client';

import { useEffect, useState, useCallback } from 'react';
import { useSession } from 'next-auth/react';
import { BookmarkPlus } from 'lucide-react';
import { useCompanyStore } from '@/stores/company';
import { CompanySelector } from '@/components/companies/CompanySelector';

interface PeerRow {
  symbol: string;
  name: string;
  health: string;
  last_price: number | null;
  market_cap: number | null;
  pe_ratio: number | null;
  pbv_ratio: number | null;
  roe: number | null;
  net_profit_margin: number | null;
  revenue_growth: number | null;
  eps_growth: number | null;
  dividend_yield: number | null;
  payout_ratio: number | null;
  price_change_1y: number | null;
  is_selected: boolean;
}

function safeNum(v: unknown): number | null {
  if (v === null || v === undefined) return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

function fmtPctColored(v: unknown): React.ReactNode {
  const n = safeNum(v);
  if (n === null) return <span style={{ color: 'var(--color-text-muted)' }}>—</span>;
  const color = n >= 0 ? 'var(--color-positive)' : 'var(--color-negative)';
  return <span style={{ color }}>{n >= 0 ? '+' : ''}{n.toFixed(2)}%</span>;
}

function fmtNeutral(v: unknown, suffix = '%'): string {
  const n = safeNum(v);
  return n !== null ? n.toFixed(2) + suffix : '—';
}

function fmtMktCap(v: unknown): string {
  const n = safeNum(v);
  if (n === null || n === 0) return '—';
  return n >= 1e12 ? `${(n / 1e12).toFixed(2)}T` : `${(n / 1e9).toFixed(1)}B`;
}

function HealthBadge({ health }: { health: string }) {
  const map: Record<string, { bg: string; color: string }> = {
    'Strong':       { bg: '#1a56db', color: '#fff' },
    'Satisfactory': { bg: '#057a55', color: '#fff' },
    'Marginal':     { bg: '#c27803', color: '#fff' },
    'Weak':         { bg: '#e02424', color: '#fff' },
    '—':            { bg: '#e5e7eb', color: '#6b7280' },
  };
  const s = map[health] ?? map['—']!;
  return (
    <span style={{
      display: 'inline-block', padding: '2px 10px', borderRadius: 4,
      fontSize: 11, fontWeight: 600, background: s.bg, color: s.color,
    }}>{health}</span>
  );
}

const COLUMNS = [
  { key: 'health',            label: 'Health',                  align: 'left'  },
  { key: 'roe',               label: 'ROE (%)',                 align: 'right' },
  { key: 'net_profit_margin', label: 'Net Profit\nMargin (%)',  align: 'right' },
  { key: 'revenue_growth',    label: 'Rev Growth\n(%)',         align: 'right' },
  { key: 'eps_growth',        label: 'EPS Growth\n(%)',         align: 'right' },
  { key: 'dividend_yield',    label: 'Dividend\nYield (%)',     align: 'right' },
  { key: 'payout_ratio',      label: 'Div Payout\n(%)',         align: 'right' },
  { key: 'price_change_1y',   label: 'Price Change\n1y (%)',    align: 'right' },
  { key: 'market_cap',        label: 'Mkt Cap',                 align: 'right' },
  { key: 'pe_ratio',          label: 'PE',                      align: 'right' },
  { key: 'pbv_ratio',         label: 'Price to\nValuat. (x)',   align: 'right' },
] as const;

type ColKey = typeof COLUMNS[number]['key'];

function renderCell(key: ColKey, row: PeerRow): React.ReactNode {
  switch (key) {
    case 'health':            return <HealthBadge health={row.health} />;
    case 'roe':               return fmtNeutral(row.roe);
    case 'net_profit_margin': return fmtNeutral(row.net_profit_margin);
    case 'revenue_growth':    return fmtPctColored(row.revenue_growth);
    case 'eps_growth':        return fmtPctColored(row.eps_growth);
    case 'dividend_yield':    return fmtNeutral(row.dividend_yield);
    case 'payout_ratio':      return fmtNeutral(row.payout_ratio);
    case 'price_change_1y':   return fmtPctColored(row.price_change_1y);
    case 'market_cap':        return fmtMktCap(row.market_cap);
    case 'pe_ratio': {
      const n = safeNum(row.pe_ratio);
      return n !== null ? n.toFixed(2) : '—';
    }
    case 'pbv_ratio': {
      const n = safeNum(row.pbv_ratio);
      return n !== null ? n.toFixed(2) + 'x' : '—';
    }
    default: return '—';
  }
}

export default function PeersPage() {
  const { data: session } = useSession();
  const { selectedSymbol } = useCompanyStore();
  const [peers, setPeers] = useState<PeerRow[]>([]);
  const [loading, setLoading] = useState(false);

  const authHeader = useCallback((): Record<string, string> => {
    const token = (session as { accessToken?: string } | null)?.accessToken;
    return token ? { Authorization: `Bearer ${token}` } : {};
  }, [session]);

  useEffect(() => {
    if (!session || !selectedSymbol) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true);
    fetch(`/api/v1/stocks/${selectedSymbol}/peers`, { headers: authHeader() })
      .then(r => r.json())
      .then((data: PeerRow[]) => { setPeers(Array.isArray(data) ? data : []); setLoading(false); })
      .catch(() => { setPeers([]); setLoading(false); });
  }, [selectedSymbol, session, authHeader]);

  return (
    <div style={{ padding: '24px 28px', display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: 4 }}>
            Peer Comparison
          </h1>
          <p style={{ fontSize: 12, color: 'var(--color-text-muted)', marginBottom: 0 }}>
            {selectedSymbol} — Key metrics vs. sector peers. Source: Yahoo Finance.
          </p>
        </div>
        <button
          type="button"
          style={{
            display: 'flex', alignItems: 'center', gap: 6,
            padding: '6px 14px', borderRadius: 6, fontSize: 12, fontWeight: 600,
            border: '1px solid var(--color-border)', background: 'white',
            color: 'var(--color-text-secondary)', cursor: 'pointer',
          }}
        >
          <BookmarkPlus size={13} />
          Save as Watchlist
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '220px 1fr', gap: 20, alignItems: 'end' }}>
        <CompanySelector />
      </div>

      {/* Health legend */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
        <span style={{ fontSize: 11, color: 'var(--color-text-muted)', fontWeight: 600 }}>Health:</span>
        {[
          { label: 'Strong',       desc: 'ROE ≥ 18%',  bg: '#1a56db' },
          { label: 'Satisfactory', desc: 'ROE 12–18%', bg: '#057a55' },
          { label: 'Marginal',     desc: 'ROE 6–12%',  bg: '#c27803' },
          { label: 'Weak',         desc: 'ROE < 6%',   bg: '#e02424' },
        ].map(({ label, desc, bg }) => (
          <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
            <span style={{
              display: 'inline-block', padding: '1px 8px', borderRadius: 3,
              fontSize: 10, fontWeight: 600, background: bg, color: '#fff',
            }}>{label}</span>
            <span style={{ fontSize: 10, color: 'var(--color-text-muted)' }}>{desc}</span>
          </div>
        ))}
      </div>

      {/* Table */}
      <div style={{ background: '#fff', border: '1px solid var(--color-border)', borderRadius: 8, overflow: 'hidden' }}>
        {loading ? (
          <div style={{ padding: 60, textAlign: 'center', color: 'var(--color-text-muted)', fontSize: 13 }}>
            Loading peer data for {selectedSymbol}… (may take 10–15s)
          </div>
        ) : peers.length === 0 ? (
          <div style={{ padding: 40, textAlign: 'center', color: 'var(--color-text-muted)', fontSize: 13 }}>
            No peer data available.
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid var(--color-border)', background: 'var(--color-bg-page)' }}>
                  <th style={{
                    padding: '10px 14px', textAlign: 'left', fontSize: 10, fontWeight: 700,
                    letterSpacing: '0.06em', textTransform: 'uppercase',
                    color: 'var(--color-text-muted)', minWidth: 70,
                    position: 'sticky', left: 0, background: 'var(--color-bg-page)',
                    borderRight: '1px solid var(--color-border)',
                  }}>Symbol</th>
                  <th style={{
                    padding: '10px 14px', textAlign: 'left', fontSize: 10, fontWeight: 700,
                    letterSpacing: '0.06em', textTransform: 'uppercase',
                    color: 'var(--color-text-muted)', minWidth: 180,
                  }}>Company</th>
                  {COLUMNS.map(col => (
                    <th key={col.key} style={{
                      padding: '8px 12px', textAlign: col.align,
                      fontSize: 10, fontWeight: 700, letterSpacing: '0.05em',
                      textTransform: 'uppercase', color: 'var(--color-text-muted)',
                      minWidth: 90, whiteSpace: 'pre-line', lineHeight: 1.3,
                    }}>{col.label}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {peers.map((p, idx) => {
                  const rowBg = p.is_selected
                    ? 'rgba(0,87,168,0.06)'
                    : idx % 2 === 0 ? 'transparent' : 'rgba(0,0,0,0.01)';
                  const stickyBg = p.is_selected
                    ? 'rgba(0,87,168,0.06)'
                    : (idx % 2 === 0 ? '#fff' : '#fafafa');
                  return (
                    <tr key={p.symbol} style={{ borderBottom: '1px solid var(--color-border-subtle)', background: rowBg }}>
                      <td style={{
                        padding: '10px 14px', position: 'sticky', left: 0,
                        background: stickyBg, borderRight: '1px solid var(--color-border)',
                        fontWeight: 700,
                        color: p.is_selected ? 'var(--color-blue-primary)' : 'var(--color-text-primary)',
                      }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          {p.is_selected && <span style={{ color: '#f59e0b', fontSize: 14 }}>★</span>}
                          <span style={{ fontFamily: 'monospace' }}>{p.symbol}</span>
                        </div>
                      </td>
                      <td style={{
                        padding: '10px 14px',
                        color: p.is_selected ? 'var(--color-blue-primary)' : 'var(--color-text-secondary)',
                        fontWeight: p.is_selected ? 600 : 400,
                        maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                      }}>{p.name}</td>
                      {COLUMNS.map(col => (
                        <td key={col.key} style={{
                          padding: '10px 12px', textAlign: col.align,
                          color: 'var(--color-text-secondary)', fontSize: 12,
                        }}>
                          {renderCell(col.key, p)}
                        </td>
                      ))}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <p style={{ fontSize: 11, color: 'var(--color-text-muted)', margin: 0 }}>
        Health score computed from ROE. All metrics from Yahoo Finance.
        Growth = year-over-year. Price change = trailing 1 year.
      </p>
    </div>
  );
}
