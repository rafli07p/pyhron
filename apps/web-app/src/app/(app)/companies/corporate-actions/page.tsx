'use client';

import { useEffect, useState, useCallback } from 'react';
import { useSession } from 'next-auth/react';
import { useCompanyStore } from '@/stores/company';

interface CorporateAction {
  symbol: string;
  action_type: string;
  ex_date: string;
  record_date: string | null;
  description: string;
  value: number | null;
}

type Filter = 'all' | 'dividend' | 'stock_split' | 'rights_issue';

const BADGE_COLORS: Record<string, { bg: string; fg: string; label: string }> = {
  dividend:     { bg: 'rgba(0,87,168,0.12)',  fg: 'var(--color-blue-primary)', label: 'Dividend' },
  stock_split:  { bg: 'rgba(229,140,0,0.14)', fg: '#C27600',                   label: 'Stock Split' },
  rights_issue: { bg: 'rgba(0,135,90,0.12)',  fg: 'var(--color-positive)',     label: 'Rights Issue' },
};

const FILTERS: { id: Filter; label: string }[] = [
  { id: 'all', label: 'All' },
  { id: 'dividend', label: 'Dividend' },
  { id: 'stock_split', label: 'Stock Split' },
  { id: 'rights_issue', label: 'Rights Issue' },
];

export default function CorporateActionsPage() {
  const { data: session } = useSession();
  const { selectedSymbol } = useCompanyStore();
  const [actions, setActions] = useState<CorporateAction[]>([]);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState<Filter>('all');

  const authHeader = useCallback((): Record<string, string> => {
    const token = (session as { accessToken?: string } | null)?.accessToken;
    return token ? { Authorization: `Bearer ${token}` } : {};
  }, [session]);

  useEffect(() => {
    if (!session || !selectedSymbol) return;
    setLoading(true);
    fetch(`/api/v1/stocks/${selectedSymbol}/corporate-actions`, { headers: authHeader() })
      .then(r => r.json())
      .then((data: CorporateAction[]) => { setActions(Array.isArray(data) ? data : []); setLoading(false); })
      .catch(() => { setActions([]); setLoading(false); });
  }, [selectedSymbol, session, authHeader]);

  const filtered = filter === 'all' ? actions : actions.filter(a => a.action_type === filter);

  return (
    <div style={{ padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div>
        <h1 style={{ fontSize: 20, fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: 4 }}>
          Corporate Actions
        </h1>
        <p style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>
          {selectedSymbol} — Dividends, stock splits, and other corporate events. Source: Yahoo Finance.
        </p>
      </div>

      <div style={{ display: 'flex', gap: 6 }}>
        {FILTERS.map(f => {
          const active = filter === f.id;
          return (
            <button
              key={f.id}
              onClick={() => setFilter(f.id)}
              style={{
                padding: '6px 12px', fontSize: 12, fontWeight: active ? 700 : 500,
                borderRadius: 4, border: '1px solid var(--color-border)',
                background: active ? 'var(--color-blue-primary)' : '#fff',
                color: active ? '#fff' : 'var(--color-text-secondary)',
                cursor: 'pointer',
              }}
            >
              {f.label}
            </button>
          );
        })}
      </div>

      <div style={{ background: '#fff', border: '1px solid var(--color-border)', borderRadius: 8, overflow: 'hidden' }}>
        {loading ? (
          <div style={{ padding: 40, textAlign: 'center', color: 'var(--color-text-muted)', fontSize: 13 }}>
            Loading {selectedSymbol}…
          </div>
        ) : filtered.length === 0 ? (
          <div style={{ padding: 40, textAlign: 'center', color: 'var(--color-text-muted)', fontSize: 13 }}>
            No {filter === 'all' ? 'corporate actions' : filter.replace('_', ' ')} recorded for {selectedSymbol}.
          </div>
        ) : (
          <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--color-border)', background: 'var(--color-bg-page)' }}>
                {['Type', 'Ex Date', 'Record Date', 'Description', 'Value (IDR)'].map(h => (
                  <th key={h} style={{
                    padding: '8px 12px', textAlign: h === 'Value (IDR)' ? 'right' : 'left',
                    fontSize: 10, fontWeight: 700, letterSpacing: '0.06em',
                    textTransform: 'uppercase', color: 'var(--color-text-muted)',
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((a, i) => {
                const badge = BADGE_COLORS[a.action_type] ?? { bg: 'rgba(138,155,176,0.14)', fg: 'var(--color-text-muted)', label: a.action_type };
                return (
                  <tr key={`${a.ex_date}-${i}`} style={{ borderBottom: '1px solid var(--color-border-subtle)' }}>
                    <td style={{ padding: '8px 12px' }}>
                      <span style={{
                        fontSize: 10, fontWeight: 700, padding: '2px 7px', borderRadius: 3,
                        background: badge.bg, color: badge.fg, letterSpacing: '0.04em',
                      }}>
                        {badge.label.toUpperCase()}
                      </span>
                    </td>
                    <td style={{ padding: '8px 12px', fontFamily: 'monospace', color: 'var(--color-text-primary)', fontWeight: 600 }}>{a.ex_date}</td>
                    <td style={{ padding: '8px 12px', fontFamily: 'monospace', color: 'var(--color-text-muted)' }}>{a.record_date ?? '—'}</td>
                    <td style={{ padding: '8px 12px', color: 'var(--color-text-secondary)' }}>{a.description}</td>
                    <td style={{ padding: '8px 12px', textAlign: 'right', fontFamily: 'monospace', color: 'var(--color-text-primary)', fontWeight: 600 }}>
                      {a.value !== null ? a.value.toLocaleString('id-ID', { maximumFractionDigits: 2 }) : '—'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
