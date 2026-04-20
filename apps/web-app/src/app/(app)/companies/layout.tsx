'use client';

import { useState, useEffect, useCallback } from 'react';
import { useSession } from 'next-auth/react';
import { usePathname, useRouter } from 'next/navigation';
import { ChevronLeft, ChevronRight, BarChart2, GitBranch, FileText, Users, TrendingUp } from 'lucide-react';
import { useCompanyStore } from '@/stores/company';

interface Instrument { symbol: string; name: string; }

const NAV_ITEMS = [
  { label: 'Index Composition Viewer', path: '/companies/index-composition', Icon: GitBranch },
  { label: 'Corporate Actions', path: '/companies/corporate-actions', Icon: FileText },
  { label: 'Financial Highlights', path: '/companies/financials', Icon: BarChart2 },
  { label: 'Ownership Structure', path: '/companies/ownership', Icon: Users },
  { label: 'Peer Comparison', path: '/companies/peers', Icon: TrendingUp },
];

export default function CompaniesLayout({ children }: { children: React.ReactNode }) {
  const { data: session } = useSession();
  const pathname = usePathname();
  const router = useRouter();
  const [collapsed, setCollapsed] = useState(false);
  const [instruments, setInstruments] = useState<Instrument[]>([]);
  const [search, setSearch] = useState('');
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const { selectedSymbol, selectedName, setSelected } = useCompanyStore();

  const authHeader = useCallback((): Record<string, string> => {
    const token = (session as { accessToken?: string } | null)?.accessToken;
    return token ? { Authorization: `Bearer ${token}` } : {};
  }, [session]);

  useEffect(() => {
    if (!session) return;
    fetch('/api/v1/stocks/', { headers: authHeader() })
      .then(r => r.json())
      .then((data: Instrument[]) => setInstruments(data))
      .catch(() => {});
  }, [session, authHeader]);

  const filtered = instruments.filter(i =>
    i.symbol.includes(search.toUpperCase()) ||
    i.name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>
      {/* Secondary Sidebar — full collapse to 0 width */}
      <aside style={{
        width: collapsed ? 0 : 220,
        minWidth: collapsed ? 0 : 220,
        borderRight: collapsed ? 'none' : '1px solid var(--color-border)',
        background: '#fff',
        display: 'flex',
        flexDirection: 'column',
        transition: 'width 0.2s ease, min-width 0.2s ease',
        overflow: 'hidden',
      }}>
        {!collapsed && (
          <>
            {/* Section header */}
            <div style={{ padding: '14px 16px 10px', borderBottom: '1px solid var(--color-border)', marginBottom: 4 }}>
              <span style={{
                fontSize: 10, fontWeight: 700, letterSpacing: '0.08em',
                textTransform: 'uppercase', color: 'var(--color-text-muted)',
              }}>
                Company Insights
              </span>
            </div>

            {/* Nav items */}
            <nav style={{ flex: 1, overflowY: 'auto', padding: '6px 0', display: 'flex', flexDirection: 'column', gap: 4 }}>
              {NAV_ITEMS.map(item => {
                const active = pathname === item.path;
                return (
                  <button
                    key={item.path}
                    onClick={() => router.push(item.path)}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 8,
                      width: '100%', padding: '10px 16px',
                      background: active ? 'rgba(0,87,168,0.08)' : 'transparent',
                      border: 'none',
                      borderLeft: active ? '3px solid var(--color-blue-primary)' : '3px solid transparent',
                      cursor: 'pointer', textAlign: 'left',
                      fontSize: 12,
                      fontWeight: active ? 700 : 400,
                      color: active ? 'var(--color-blue-primary)' : 'var(--color-text-secondary)',
                    }}
                  >
                    <item.Icon size={13} style={{ flexShrink: 0 }} />
                    <span style={{ lineHeight: 1.3 }}>{item.label}</span>
                  </button>
                );
              })}
            </nav>
          </>
        )}
      </aside>

      {/* Main content area */}
      <div style={{ flex: 1, overflow: 'auto', display: 'flex', flexDirection: 'column' }}>
        {/* Company selector bar */}
        <div style={{
          padding: '10px 20px',
          borderBottom: '1px solid var(--color-border)',
          background: '#fff',
          display: 'flex', alignItems: 'center', gap: 12,
          flexShrink: 0,
        }}>
          {/* Inline toggle button */}
          <button
            onClick={() => setCollapsed(c => !c)}
            style={{
              width: 24, height: 24, borderRadius: 4,
              background: 'transparent', border: '1px solid var(--color-border)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              cursor: 'pointer', flexShrink: 0,
            }}
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed
              ? <ChevronRight size={12} style={{ color: 'var(--color-text-muted)' }} />
              : <ChevronLeft size={12} style={{ color: 'var(--color-text-muted)' }} />
            }
          </button>
          <span style={{
            fontSize: 10, fontWeight: 700, color: 'var(--color-text-muted)',
            textTransform: 'uppercase', letterSpacing: '0.08em', flexShrink: 0,
          }}>
            Company
          </span>
          {/* Dropdown */}
          <div style={{ position: 'relative' }}>
            <button
              onClick={() => setDropdownOpen(o => !o)}
              style={{
                display: 'flex', alignItems: 'center', gap: 8,
                padding: '5px 10px', borderRadius: 4, fontSize: 13, fontWeight: 600,
                border: '1px solid var(--color-border)',
                background: 'var(--color-bg-card)',
                color: 'var(--color-text-primary)',
                cursor: 'pointer', minWidth: 260,
                justifyContent: 'space-between',
              }}
            >
              <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {selectedSymbol} — {selectedName}
              </span>
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ flexShrink: 0 }}>
                <polyline points="6 9 12 15 18 9" />
              </svg>
            </button>
            {dropdownOpen && (
              <div style={{
                position: 'absolute', top: '100%', left: 0, zIndex: 100,
                background: '#fff', border: '1px solid var(--color-border)',
                borderRadius: 6, boxShadow: '0 4px 20px rgba(0,0,0,0.12)',
                width: 320, maxHeight: 300, overflow: 'hidden',
                display: 'flex', flexDirection: 'column', marginTop: 4,
              }}>
                <div style={{ padding: '8px 10px', borderBottom: '1px solid var(--color-border)' }}>
                  <input
                    autoFocus
                    value={search}
                    onChange={e => setSearch(e.target.value)}
                    placeholder="Search symbol or company…"
                    style={{
                      width: '100%', padding: '5px 8px', fontSize: 12,
                      border: '1px solid var(--color-border)', borderRadius: 4,
                      background: 'var(--color-bg-page)',
                      color: 'var(--color-text-primary)', outline: 'none',
                    }}
                  />
                </div>
                <div style={{ overflowY: 'auto', flex: 1 }}>
                  {filtered.map(i => (
                    <button
                      key={i.symbol}
                      onClick={() => {
                        setSelected(i.symbol, i.name);
                        setDropdownOpen(false);
                        setSearch('');
                      }}
                      style={{
                        display: 'flex', alignItems: 'center', gap: 10,
                        width: '100%', padding: '7px 12px', textAlign: 'left',
                        background: i.symbol === selectedSymbol ? 'rgba(0,87,168,0.06)' : 'transparent',
                        border: 'none', cursor: 'pointer', fontSize: 12,
                        color: 'var(--color-text-primary)',
                        borderBottom: '1px solid var(--color-border-subtle)',
                      }}
                    >
                      <span style={{
                        fontWeight: 700, color: 'var(--color-blue-primary)',
                        minWidth: 48, fontFamily: 'monospace', fontSize: 11,
                      }}>
                        {i.symbol}
                      </span>
                      <span style={{
                        color: 'var(--color-text-secondary)',
                        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                      }}>
                        {i.name}
                      </span>
                      {i.symbol === selectedSymbol && (
                        <svg style={{ marginLeft: 'auto', flexShrink: 0 }} width="13" height="13"
                          viewBox="0 0 24 24" fill="none" stroke="var(--color-blue-primary)" strokeWidth="2.5">
                          <polyline points="20 6 9 17 4 12" />
                        </svg>
                      )}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Page content */}
        <div style={{ flex: 1, overflow: 'auto' }}>
          {children}
        </div>
      </div>
    </div>
  );
}
