'use client';

import { useEffect, useState, useCallback } from 'react';
import { useSession } from 'next-auth/react';
import { useCompanyStore } from '@/stores/company';

interface FinancialSummary {
  symbol: string;
  period: string;
  revenue: number | null;
  net_income: number | null;
  eps: number | null;
  pe_ratio: number | null;
  pbv_ratio: number | null;
  roe: number | null;
  der: number | null;
}

type PeriodType = 'annual' | 'quarterly';

const CARD: React.CSSProperties = {
  background: '#fff', border: '1px solid var(--color-border)',
  borderRadius: 8, padding: '14px 16px',
};

function fmtLarge(v: number | null): string {
  if (v === null || v === undefined) return '—';
  const abs = Math.abs(v);
  if (abs >= 1e12) return `${(v / 1e12).toFixed(2)}T`;
  if (abs >= 1e9) return `${(v / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `${(v / 1e6).toFixed(1)}M`;
  return v.toLocaleString('id-ID');
}
function fmtPct(v: number | null): string {
  if (v === null || v === undefined) return '—';
  // yfinance returns ROE as fraction (0.18 = 18%)
  return `${(v * 100).toFixed(2)}%`;
}
function fmtRatio(v: number | null): string {
  if (v === null || v === undefined) return '—';
  return `${v.toFixed(2)}x`;
}

export default function FinancialsPage() {
  const { data: session } = useSession();
  const { selectedSymbol } = useCompanyStore();
  const [rows, setRows] = useState<FinancialSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [periodType, setPeriodType] = useState<PeriodType>('annual');

  const authHeader = useCallback((): Record<string, string> => {
    const token = (session as { accessToken?: string } | null)?.accessToken;
    return token ? { Authorization: `Bearer ${token}` } : {};
  }, [session]);

  useEffect(() => {
    if (!session || !selectedSymbol) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true);
    fetch(`/api/v1/stocks/${selectedSymbol}/financials?period_type=${periodType}`, { headers: authHeader() })
      .then(r => r.json())
      .then((data: FinancialSummary[]) => { setRows(Array.isArray(data) ? data : []); setLoading(false); })
      .catch(() => { setRows([]); setLoading(false); });
  }, [selectedSymbol, periodType, session, authHeader]);

  const latest = rows[0];

  return (
    <div style={{ padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div>
        <h1 style={{ fontSize: 20, fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: 4 }}>
          Financial Highlights
        </h1>
        <p style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>
          {selectedSymbol} — Revenue, net income, EPS, and key ratios.
        </p>
      </div>

      <div style={{ display: 'flex', gap: 6 }}>
        {(['annual', 'quarterly'] as const).map(p => {
          const active = periodType === p;
          return (
            <button
              key={p}
              onClick={() => setPeriodType(p)}
              style={{
                padding: '6px 14px', fontSize: 12, fontWeight: active ? 700 : 500,
                borderRadius: 4, border: '1px solid var(--color-border)',
                background: active ? 'var(--color-blue-primary)' : '#fff',
                color: active ? '#fff' : 'var(--color-text-secondary)',
                cursor: 'pointer', textTransform: 'capitalize',
              }}
            >
              {p}
            </button>
          );
        })}
      </div>

      {latest && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 }}>
          {[
            { label: 'P/E Ratio', value: fmtRatio(latest.pe_ratio) },
            { label: 'P/BV', value: fmtRatio(latest.pbv_ratio) },
            { label: 'ROE', value: fmtPct(latest.roe) },
            { label: 'Revenue (latest)', value: fmtLarge(latest.revenue) },
          ].map(({ label, value }) => (
            <div key={label} style={CARD}>
              <div style={{ fontSize: 10, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 4 }}>
                {label}
              </div>
              <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--color-text-primary)', fontFamily: 'monospace' }}>
                {value}
              </div>
            </div>
          ))}
        </div>
      )}

      <div style={{ background: '#fff', border: '1px solid var(--color-border)', borderRadius: 8, overflow: 'hidden' }}>
        {loading ? (
          <div style={{ padding: 40, textAlign: 'center', color: 'var(--color-text-muted)', fontSize: 13 }}>
            Loading {selectedSymbol}…
          </div>
        ) : rows.length === 0 ? (
          <div style={{ padding: 40, textAlign: 'center', color: 'var(--color-text-muted)', fontSize: 13 }}>
            No {periodType} financial data available for {selectedSymbol}.
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--color-border)', background: 'var(--color-bg-page)' }}>
                  <th style={{ padding: '8px 12px', textAlign: 'left', fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--color-text-muted)' }}>
                    Metric
                  </th>
                  {rows.map(r => (
                    <th key={r.period} style={{ padding: '8px 12px', textAlign: 'right', fontSize: 10, fontWeight: 700, letterSpacing: '0.06em', color: 'var(--color-text-muted)', whiteSpace: 'nowrap' }}>
                      {r.period}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {([
                  ['Revenue', rows.map(r => fmtLarge(r.revenue))],
                  ['Net Income', rows.map(r => fmtLarge(r.net_income))],
                  ['EPS (IDR)', rows.map(r => r.eps !== null ? r.eps.toFixed(2) : '—')],
                  ['P/E Ratio', rows.map(r => fmtRatio(r.pe_ratio))],
                  ['P/BV Ratio', rows.map(r => fmtRatio(r.pbv_ratio))],
                  ['ROE', rows.map(r => fmtPct(r.roe))],
                ] as const).map(([label, values]) => (
                  <tr key={label} style={{ borderBottom: '1px solid var(--color-border-subtle)' }}>
                    <td style={{ padding: '8px 12px', fontWeight: 600, color: 'var(--color-text-primary)' }}>
                      {label}
                    </td>
                    {values.map((v, i) => (
                      <td key={i} style={{ padding: '8px 12px', textAlign: 'right', fontFamily: 'monospace', color: 'var(--color-text-primary)' }}>
                        {v}
                      </td>
                    ))}
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
