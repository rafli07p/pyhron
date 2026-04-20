'use client';

import { useEffect, useState, useCallback } from 'react';
import { useSession } from 'next-auth/react';
import { useCompanyStore } from '@/stores/company';

interface OwnershipEntry {
  holder_name: string;
  holder_type: 'insider' | 'institution' | 'public' | string;
  shares_held: number;
  ownership_pct: number;
  change_from_prior: number | null;
}

const TYPE_COLORS: Record<string, string> = {
  insider: 'var(--color-negative)',
  institution: 'var(--color-blue-primary)',
  public: 'var(--color-positive)',
};

const CARD: React.CSSProperties = {
  background: '#fff', border: '1px solid var(--color-border)',
  borderRadius: 8, padding: '16px 18px',
};

export default function OwnershipPage() {
  const { data: session } = useSession();
  const { selectedSymbol } = useCompanyStore();
  const [entries, setEntries] = useState<OwnershipEntry[]>([]);
  const [loading, setLoading] = useState(false);

  const authHeader = useCallback((): Record<string, string> => {
    const token = (session as { accessToken?: string } | null)?.accessToken;
    return token ? { Authorization: `Bearer ${token}` } : {};
  }, [session]);

  useEffect(() => {
    if (!session || !selectedSymbol) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true);
    fetch(`/api/v1/stocks/${selectedSymbol}/ownership`, { headers: authHeader() })
      .then(r => r.json())
      .then((data: OwnershipEntry[]) => { setEntries(Array.isArray(data) ? data : []); setLoading(false); })
      .catch(() => { setEntries([]); setLoading(false); });
  }, [selectedSymbol, session, authHeader]);

  const cards = (['insider', 'institution', 'public'] as const).map(type => {
    const entry = entries.find(e => e.holder_type === type);
    const labels = { insider: 'Insider', institution: 'Institutional', public: 'Public / Retail' } as const;
    return {
      type,
      label: labels[type],
      pct: entry?.ownership_pct ?? 0,
      color: TYPE_COLORS[type],
    };
  });

  return (
    <div style={{ padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div>
        <h1 style={{ fontSize: 20, fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: 4 }}>
          Ownership Structure
        </h1>
        <p style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>
          {selectedSymbol} — Insider, institutional, and public ownership breakdown. Source: Yahoo Finance.
        </p>
      </div>

      {loading ? (
        <div style={{ padding: 40, textAlign: 'center', color: 'var(--color-text-muted)', fontSize: 13, background: '#fff', border: '1px solid var(--color-border)', borderRadius: 8 }}>
          Loading {selectedSymbol}…
        </div>
      ) : entries.length === 0 ? (
        <div style={{ padding: 40, textAlign: 'center', color: 'var(--color-text-muted)', fontSize: 13, background: '#fff', border: '1px solid var(--color-border)', borderRadius: 8 }}>
          No ownership data available for {selectedSymbol}.
        </div>
      ) : (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
            {cards.map(c => (
              <div key={c.type} style={CARD}>
                <div style={{ fontSize: 10, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8 }}>
                  {c.label}
                </div>
                <div style={{ fontSize: 28, fontWeight: 700, color: 'var(--color-text-primary)', fontFamily: 'monospace', lineHeight: 1 }}>
                  {c.pct.toFixed(2)}%
                </div>
                <div style={{ marginTop: 12, height: 6, background: 'var(--color-border-subtle)', borderRadius: 3, overflow: 'hidden' }}>
                  <div style={{ width: `${Math.min(100, c.pct)}%`, height: '100%', background: c.color, transition: 'width 0.3s ease' }} />
                </div>
              </div>
            ))}
          </div>

          <div style={{ background: '#fff', border: '1px solid var(--color-border)', borderRadius: 8, overflow: 'hidden' }}>
            <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--color-border)', background: 'var(--color-bg-page)' }}>
                  {['Holder Name', 'Type', 'Ownership %', 'Change'].map(h => (
                    <th key={h} style={{
                      padding: '8px 12px', textAlign: h === 'Holder Name' || h === 'Type' ? 'left' : 'right',
                      fontSize: 10, fontWeight: 700, letterSpacing: '0.06em',
                      textTransform: 'uppercase', color: 'var(--color-text-muted)',
                    }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {entries.map(e => (
                  <tr key={e.holder_name} style={{ borderBottom: '1px solid var(--color-border-subtle)' }}>
                    <td style={{ padding: '10px 12px', fontWeight: 600, color: 'var(--color-text-primary)' }}>{e.holder_name}</td>
                    <td style={{ padding: '10px 12px' }}>
                      <span style={{
                        fontSize: 10, fontWeight: 700, padding: '2px 7px', borderRadius: 3,
                        background: 'rgba(138,155,176,0.14)',
                        color: TYPE_COLORS[e.holder_type] ?? 'var(--color-text-muted)',
                        textTransform: 'uppercase', letterSpacing: '0.04em',
                      }}>
                        {e.holder_type}
                      </span>
                    </td>
                    <td style={{ padding: '10px 12px', textAlign: 'right', fontFamily: 'monospace', fontWeight: 700, color: 'var(--color-text-primary)' }}>
                      {e.ownership_pct.toFixed(2)}%
                    </td>
                    <td style={{ padding: '10px 12px', textAlign: 'right', fontFamily: 'monospace', color: 'var(--color-text-muted)' }}>
                      {e.change_from_prior !== null ? `${e.change_from_prior > 0 ? '+' : ''}${e.change_from_prior.toFixed(2)}%` : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <p style={{ fontSize: 11, color: 'var(--color-text-muted)', fontStyle: 'italic' }}>
            Source: Yahoo Finance. Institutional breakdown sourced from major_holders.
          </p>
        </>
      )}
    </div>
  );
}
