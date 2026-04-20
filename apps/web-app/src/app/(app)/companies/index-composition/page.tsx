'use client';

import { useEffect, useState, useCallback } from 'react';
import { useSession } from 'next-auth/react';
import { useCompanyStore } from '@/stores/company';

interface StockProfile {
  symbol: string;
  name: string;
  exchange: string;
  sector: string | null;
  industry: string | null;
  listing_date: string | null;
  market_cap: number | null;
  last_price: number | null;
  shares_outstanding: number | null;
  is_lq45: boolean;
  description: string | null;
}

const fmtPrice = (v: number | null) => v ? v.toLocaleString('id-ID') : '—';
const fmtMktCap = (v: number | null) => {
  if (!v) return '—';
  return v >= 1e12 ? `IDR ${(v / 1e12).toFixed(2)}T` : `IDR ${(v / 1e9).toFixed(1)}B`;
};
const fmtShares = (v: number | null) => (v ? `${(v / 1e9).toFixed(2)}B` : '—');

const SECTION_HEADER: React.CSSProperties = {
  fontSize: 10, fontWeight: 700, textTransform: 'uppercase',
  letterSpacing: '0.08em', color: 'var(--color-text-muted)', marginBottom: 12,
};
const CARD: React.CSSProperties = {
  background: '#fff', border: '1px solid var(--color-border)',
  borderRadius: 8, padding: '14px 16px',
};

// Index membership rows — known LQ45 / IDX30 / IDX80 / IHSG constituents
const IDX30_SYMBOLS = new Set(['BBCA','BBRI','BMRI','TLKM','ASII','BBNI','UNVR','GOTO','ICBP','INDF','KLBF','SMGR','UNTR','ADRO','PTBA','ITMG','GGRM','HMSP','CPIN','JPFA','BSDE','PWON','LPPF','MNCN','BRIS','BTPS','ARTO','EMTK','MAPI','TBIG']);
const IDX80_EXTRA = new Set(['EXCL','ISAT','FREN','MEDC','PGAS','INCO','ANTM','TINS','AKRA','BRPT','TPIA','INTP','WIKA','WSKT','PTPP','ADHI','JSMR','WSBP','ESSA','MIKA']);

function membership(symbol: string, isLq45: boolean) {
  return [
    { index: 'IHSG', active: true, note: 'All listed IDX equities' },
    { index: 'LQ45', active: isLq45, note: isLq45 ? 'Top 45 by liquidity & market cap' : 'Not currently included' },
    { index: 'IDX30', active: IDX30_SYMBOLS.has(symbol), note: IDX30_SYMBOLS.has(symbol) ? 'Top 30 LQ45 constituents' : 'Not currently included' },
    { index: 'IDX80', active: IDX30_SYMBOLS.has(symbol) || IDX80_EXTRA.has(symbol), note: 'Mid-cap growth index' },
  ];
}

export default function IndexCompositionPage() {
  const { data: session } = useSession();
  const { selectedSymbol } = useCompanyStore();
  const [profile, setProfile] = useState<StockProfile | null>(null);
  const [loading, setLoading] = useState(false);

  const authHeader = useCallback((): Record<string, string> => {
    const token = (session as { accessToken?: string } | null)?.accessToken;
    return token ? { Authorization: `Bearer ${token}` } : {};
  }, [session]);

  useEffect(() => {
    if (!session || !selectedSymbol) return;
    setLoading(true);
    fetch(`/api/v1/stocks/${selectedSymbol}`, { headers: authHeader() })
      .then(r => r.json())
      .then((data: StockProfile) => { setProfile(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, [selectedSymbol, session, authHeader]);

  if (loading) return (
    <div style={{ padding: 40, textAlign: 'center', color: 'var(--color-text-muted)', fontSize: 13 }}>
      Loading {selectedSymbol}…
    </div>
  );

  const kpis: { label: string; value: string }[] = profile
    ? [
        { label: 'Last Price (IDR)', value: fmtPrice(profile.last_price) },
        { label: 'Market Cap', value: fmtMktCap(profile.market_cap) },
        { label: 'Shares Outstanding', value: fmtShares(profile.shares_outstanding) },
        { label: 'Sector', value: profile.sector ?? '—' },
        { label: 'LQ45 Member', value: profile.is_lq45 ? 'Yes' : 'No' },
      ]
    : [];

  return (
    <div style={{ padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div>
        <h1 style={{ fontSize: 20, fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: 4 }}>
          Index Composition Viewer
        </h1>
        {profile && (
          <p style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>
            Industry: {profile.industry ?? '—'}
          </p>
        )}
      </div>

      {profile && (
        <div style={{
          display: 'flex', gap: 24, padding: '12px 16px',
          background: '#fff', border: '1px solid var(--color-border)', borderRadius: 8,
        }}>
          {kpis.map(({ label, value }, i) => (
            <div
              key={label}
              style={{
                borderRight: i < kpis.length - 1 ? '1px solid var(--color-border)' : 'none',
                paddingRight: i < kpis.length - 1 ? 24 : 0,
              }}
            >
              <div style={{ fontSize: 10, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 4 }}>
                {label}
              </div>
              <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--color-text-primary)', fontFamily: 'monospace' }}>
                {value}
              </div>
            </div>
          ))}
        </div>
      )}

      {profile && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <div style={CARD}>
            <p style={SECTION_HEADER}>Company Overview</p>
            <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
              <tbody>
                {([
                  ['Symbol', profile.symbol],
                  ['Full Name', profile.name],
                  ['Exchange', profile.exchange ?? 'IDX'],
                  ['Sector', profile.sector ?? '—'],
                  ['Industry', profile.industry ?? '—'],
                  ['Listing Date', profile.listing_date ?? '—'],
                  ['LQ45 Member', profile.is_lq45 ? 'Yes' : 'No'],
                ] as const).map(([k, v]) => (
                  <tr key={k} style={{ borderBottom: '1px solid var(--color-border-subtle)' }}>
                    <td style={{ padding: '7px 0', color: 'var(--color-text-muted)', width: '40%', fontSize: 11 }}>{k}</td>
                    <td style={{ padding: '7px 0', fontWeight: 600, color: 'var(--color-text-primary)' }}>{v}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div style={CARD}>
            <p style={SECTION_HEADER}>Business Description</p>
            <p style={{ fontSize: 12, color: 'var(--color-text-secondary)', lineHeight: 1.7 }}>
              {profile.description ?? 'No description available from data provider.'}
            </p>
          </div>
        </div>
      )}

      {profile && (
        <div style={CARD}>
          <p style={SECTION_HEADER}>Index Membership</p>
          <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--color-border)' }}>
                <th style={{ padding: '8px 0', textAlign: 'left', fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--color-text-muted)' }}>Index Name</th>
                <th style={{ padding: '8px 0', textAlign: 'left', fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--color-text-muted)' }}>Description</th>
                <th style={{ padding: '8px 0', textAlign: 'right', fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--color-text-muted)' }}>Weight %</th>
                <th style={{ padding: '8px 0', textAlign: 'right', fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--color-text-muted)' }}>Status</th>
              </tr>
            </thead>
            <tbody>
              {membership(profile.symbol, profile.is_lq45).map(row => (
                <tr key={row.index} style={{ borderBottom: '1px solid var(--color-border-subtle)' }}>
                  <td style={{ padding: '8px 0', fontWeight: 700, color: 'var(--color-blue-primary)', fontFamily: 'monospace' }}>{row.index}</td>
                  <td style={{ padding: '8px 0', color: 'var(--color-text-secondary)', fontSize: 11 }}>{row.note}</td>
                  <td style={{ padding: '8px 0', textAlign: 'right', color: 'var(--color-text-muted)', fontFamily: 'monospace' }}>—</td>
                  <td style={{ padding: '8px 0', textAlign: 'right' }}>
                    <span style={{
                      fontSize: 10, fontWeight: 700, padding: '2px 6px', borderRadius: 3,
                      background: row.active ? 'rgba(0,135,90,0.12)' : 'rgba(138,155,176,0.14)',
                      color: row.active ? 'var(--color-positive)' : 'var(--color-text-muted)',
                    }}>
                      {row.active ? 'ACTIVE' : 'NOT LISTED'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
