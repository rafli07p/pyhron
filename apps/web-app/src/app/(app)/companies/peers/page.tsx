'use client';

import { useEffect, useState, useCallback } from 'react';
import { useSession } from 'next-auth/react';
import { useCompanyStore } from '@/stores/company';

interface PeerRow {
  symbol: string;
  name: string;
  last_price: number | null;
  market_cap: number | null;
  pe_ratio: number | null;
  pbv_ratio: number | null;
  roe: number | null;
  dividend_yield: number | null;
  is_selected: boolean;
}

const fmtPrice = (v: number | null) => v ? v.toLocaleString('id-ID') : '—';
const fmtMktCap = (v: number | null) => {
  if (!v) return '—';
  return v >= 1e12 ? `${(v / 1e12).toFixed(2)}T` : `${(v / 1e9).toFixed(1)}B`;
};
const fmtRatio = (v: number | null) => v !== null && v !== undefined ? `${v.toFixed(2)}x` : '—';
const fmtPct = (v: number | null) => {
  if (v === null || v === undefined) return '—';
  return `${(v * 100).toFixed(2)}%`;
};

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
    <div style={{ padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div>
        <h1 style={{ fontSize: 20, fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: 4 }}>
          Peer Comparison
        </h1>
        <p style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>
          {selectedSymbol} — Key metrics vs. sector peers. Source: Yahoo Finance.
        </p>
      </div>

      <div style={{ background: '#fff', border: '1px solid var(--color-border)', borderRadius: 8, overflow: 'hidden' }}>
        {loading ? (
          <div style={{ padding: 40, textAlign: 'center', color: 'var(--color-text-muted)', fontSize: 13 }}>
            Loading peers for {selectedSymbol}… (may take 5–10s)
          </div>
        ) : peers.length === 0 ? (
          <div style={{ padding: 40, textAlign: 'center', color: 'var(--color-text-muted)', fontSize: 13 }}>
            No peer data available for {selectedSymbol}.
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--color-border)', background: 'var(--color-bg-page)' }}>
                  {['Symbol', 'Company', 'Price (IDR)', 'Mkt Cap', 'P/E', 'P/BV', 'ROE', 'Div Yield'].map(h => (
                    <th key={h} style={{
                      padding: '8px 12px', textAlign: h === 'Symbol' || h === 'Company' ? 'left' : 'right',
                      fontSize: 10, fontWeight: 700, letterSpacing: '0.06em',
                      textTransform: 'uppercase', color: 'var(--color-text-muted)', whiteSpace: 'nowrap',
                    }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {peers.map(p => (
                  <tr
                    key={p.symbol}
                    style={{
                      borderBottom: '1px solid var(--color-border-subtle)',
                      background: p.is_selected ? 'rgba(0,87,168,0.06)' : 'transparent',
                    }}
                  >
                    <td style={{
                      padding: '9px 12px', fontFamily: 'monospace', fontWeight: 700,
                      color: p.is_selected ? 'var(--color-blue-primary)' : 'var(--color-text-primary)',
                    }}>
                      {p.symbol}
                      {p.is_selected && (
                        <span style={{
                          marginLeft: 8, fontSize: 9, padding: '1px 5px', borderRadius: 3,
                          background: 'var(--color-blue-primary)', color: '#fff', letterSpacing: '0.04em',
                        }}>
                          SELECTED
                        </span>
                      )}
                    </td>
                    <td style={{ padding: '9px 12px', color: 'var(--color-text-secondary)', maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {p.name}
                    </td>
                    <td style={{ padding: '9px 12px', textAlign: 'right', fontFamily: 'monospace', fontWeight: 600, color: 'var(--color-text-primary)' }}>
                      {fmtPrice(p.last_price)}
                    </td>
                    <td style={{ padding: '9px 12px', textAlign: 'right', fontFamily: 'monospace', color: 'var(--color-text-secondary)' }}>
                      {fmtMktCap(p.market_cap)}
                    </td>
                    <td style={{ padding: '9px 12px', textAlign: 'right', fontFamily: 'monospace', color: 'var(--color-text-secondary)' }}>
                      {fmtRatio(p.pe_ratio)}
                    </td>
                    <td style={{ padding: '9px 12px', textAlign: 'right', fontFamily: 'monospace', color: 'var(--color-text-secondary)' }}>
                      {fmtRatio(p.pbv_ratio)}
                    </td>
                    <td style={{ padding: '9px 12px', textAlign: 'right', fontFamily: 'monospace', color: 'var(--color-text-secondary)' }}>
                      {fmtPct(p.roe)}
                    </td>
                    <td style={{ padding: '9px 12px', textAlign: 'right', fontFamily: 'monospace', color: 'var(--color-text-secondary)' }}>
                      {fmtPct(p.dividend_yield)}
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
