'use client';

import { useEffect, useState, useCallback } from 'react';
import { useSession } from 'next-auth/react';
import { useCompanyStore } from '@/stores/company';
import { CompanySelector } from '@/components/companies/CompanySelector';

interface PeerRow {
  symbol: string;
  name: string;
  last_price: number | string | null;
  market_cap: number | string | null;
  pe_ratio: number | string | null;
  pbv_ratio: number | string | null;
  roe: number | string | null;
  dividend_yield: number | string | null;
  is_selected: boolean;
}

function safeNum(v: unknown): number | null {
  if (v === null || v === undefined) return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

const fmtPrice = (v: unknown) => {
  const n = safeNum(v);
  return n !== null && n > 0 ? n.toLocaleString('id-ID') : '—';
};
const fmtMktCap = (v: unknown) => {
  const n = safeNum(v);
  if (n === null || n === 0) return '—';
  return n >= 1e12 ? `${(n / 1e12).toFixed(2)}T` : `${(n / 1e9).toFixed(1)}B`;
};
const fmtRatio = (v: unknown) => {
  const n = safeNum(v);
  return n !== null ? `${n.toFixed(2)}x` : '—';
};
// Backend returns ROE as fraction (0.18 = 18%).
const fmtRoePct = (v: unknown) => {
  const n = safeNum(v);
  return n !== null ? `${(n * 100).toFixed(2)}%` : '—';
};
// Backend returns dividend_yield pre-multiplied (e.g. 5.23 = 5.23%).
const fmtYieldPct = (v: unknown) => {
  const n = safeNum(v);
  return n !== null ? `${n.toFixed(2)}%` : '—';
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
    <div style={{ padding: '24px 28px', display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div>
        <h1 style={{ fontSize: 20, fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: 4 }}>
          Peer Comparison
        </h1>
        <p style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>
          {selectedSymbol} — Key metrics vs. sector peers. Source: Yahoo Finance.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '220px 1fr', gap: 20, alignItems: 'end' }}>
        <CompanySelector />
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
                      padding: '10px 14px', textAlign: h === 'Symbol' || h === 'Company' ? 'left' : 'right',
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
                      padding: '10px 14px', fontFamily: 'monospace', fontWeight: 700,
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
                    <td style={{ padding: '10px 14px', color: 'var(--color-text-secondary)', maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {p.name}
                    </td>
                    <td style={{ padding: '10px 14px', textAlign: 'right', fontFamily: 'monospace', fontWeight: 600, color: 'var(--color-text-primary)' }}>
                      {fmtPrice(p.last_price)}
                    </td>
                    <td style={{ padding: '10px 14px', textAlign: 'right', fontFamily: 'monospace', color: 'var(--color-text-secondary)' }}>
                      {fmtMktCap(p.market_cap)}
                    </td>
                    <td style={{ padding: '10px 14px', textAlign: 'right', fontFamily: 'monospace', color: 'var(--color-text-secondary)' }}>
                      {fmtRatio(p.pe_ratio)}
                    </td>
                    <td style={{ padding: '10px 14px', textAlign: 'right', fontFamily: 'monospace', color: 'var(--color-text-secondary)' }}>
                      {fmtRatio(p.pbv_ratio)}
                    </td>
                    <td style={{ padding: '10px 14px', textAlign: 'right', fontFamily: 'monospace', color: 'var(--color-text-secondary)' }}>
                      {fmtRoePct(p.roe)}
                    </td>
                    <td style={{ padding: '10px 14px', textAlign: 'right', fontFamily: 'monospace', color: 'var(--color-text-secondary)' }}>
                      {fmtYieldPct(p.dividend_yield)}
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
