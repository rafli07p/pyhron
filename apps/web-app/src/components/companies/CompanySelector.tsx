'use client';

import { useCallback, useEffect, useState } from 'react';
import { useSession } from 'next-auth/react';
import { useCompanyStore } from '@/stores/company';

interface Instrument { symbol: string; name: string; }

/**
 * Reusable company dropdown synced with useCompanyStore.
 * Matches the control in /companies/index-composition exactly.
 */
export function CompanySelector({ width = 220 }: { width?: number }) {
  const { data: session } = useSession();
  const { selectedSymbol, setSelected } = useCompanyStore();
  const [instruments, setInstruments] = useState<Instrument[]>([]);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [search, setSearch] = useState('');

  const authHeader = useCallback((): Record<string, string> => {
    const token = (session as { accessToken?: string } | null)?.accessToken;
    return token ? { Authorization: `Bearer ${token}` } : {};
  }, [session]);

  useEffect(() => {
    if (!session) return;
    fetch('/api/v1/stocks/', { headers: authHeader() })
      .then(r => r.json())
      .then((data: Instrument[]) => setInstruments(Array.isArray(data) ? data : []))
      .catch(() => {});
  }, [session, authHeader]);

  const filtered = instruments.filter(i =>
    i.symbol.includes(search.toUpperCase()) ||
    i.name.toLowerCase().includes(search.toLowerCase()),
  );

  return (
    <div style={{ width }}>
      <label style={{
        fontSize: 10, fontWeight: 700, textTransform: 'uppercase',
        letterSpacing: '0.08em', color: 'var(--color-text-muted)',
        display: 'block', marginBottom: 4,
      }}>
        Company
      </label>
      <div style={{ position: 'relative' }}>
        <button
          type="button"
          onClick={() => setDropdownOpen(o => !o)}
          style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            width: '100%', padding: '6px 10px', fontSize: 13, fontWeight: 600,
            border: '1px solid var(--color-border)', borderRadius: 4,
            background: 'white', color: 'var(--color-text-primary)', cursor: 'pointer',
          }}
        >
          <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {selectedSymbol}
          </span>
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ flexShrink: 0 }}>
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </button>
        {dropdownOpen && (
          <div style={{
            position: 'absolute', top: '100%', left: 0, zIndex: 50,
            background: 'white', border: '1px solid var(--color-border)',
            borderRadius: 6, boxShadow: '0 4px 16px rgba(0,0,0,0.12)',
            width: 300, maxHeight: 280, overflow: 'hidden',
            display: 'flex', flexDirection: 'column', marginTop: 4,
          }}>
            <div style={{ padding: '8px 10px', borderBottom: '1px solid var(--color-border)' }}>
              <input
                autoFocus
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder="Search…"
                style={{
                  width: '100%', padding: '4px 8px', fontSize: 12,
                  border: '1px solid var(--color-border)', borderRadius: 4,
                  outline: 'none', background: 'var(--color-bg-page)',
                }}
              />
            </div>
            <div style={{ overflowY: 'auto', flex: 1 }}>
              {filtered.map(i => (
                <button
                  key={i.symbol}
                  type="button"
                  onClick={() => {
                    setSelected(i.symbol, i.name);
                    setDropdownOpen(false);
                    setSearch('');
                  }}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 8,
                    width: '100%', padding: '7px 12px', fontSize: 12,
                    background: i.symbol === selectedSymbol ? 'rgba(0,87,168,0.06)' : 'transparent',
                    border: 'none', cursor: 'pointer', textAlign: 'left',
                    borderBottom: '1px solid var(--color-border-subtle)',
                  }}
                >
                  <span style={{
                    fontWeight: 700, color: 'var(--color-blue-primary)',
                    minWidth: 46, fontFamily: 'monospace', fontSize: 11,
                  }}>
                    {i.symbol}
                  </span>
                  <span style={{
                    color: 'var(--color-text-secondary)',
                    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                  }}>
                    {i.name}
                  </span>
                </button>
              ))}
              {filtered.length === 0 && (
                <div style={{ padding: 20, textAlign: 'center', fontSize: 12, color: 'var(--color-text-muted)' }}>
                  No matches
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
