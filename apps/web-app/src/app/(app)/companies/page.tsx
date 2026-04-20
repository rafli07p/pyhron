'use client';

import { useState, useEffect, useCallback } from 'react';
import { useSession } from 'next-auth/react';
import { Building2, TrendingUp, FileText, Users } from 'lucide-react';

interface Instrument { symbol: string; name: string; }
interface StockProfile {
  symbol: string; name: string; exchange: string;
  sector: string | null; industry: string | null;
  listing_date: string | null; market_cap: number | null;
  last_price: number | null; shares_outstanding: number | null;
  is_lq45: boolean; description: string | null;
}

function fmtPrice(v: number | null) {
  if (!v) return '—';
  return v.toLocaleString('id-ID');
}
function fmtMktCap(v: number | null) {
  if (!v) return '—';
  const t = v / 1e12;
  if (t >= 1) return `IDR ${t.toFixed(2)}T`;
  return `IDR ${(v / 1e9).toFixed(1)}B`;
}
function fmtShares(v: number | null) {
  if (!v) return '—';
  return (v / 1e9).toFixed(2) + 'B shares';
}

const TABS = [
  { id: 'profile', label: 'Company Profile', Icon: Building2 },
  { id: 'index', label: 'Index Composition', Icon: TrendingUp },
  { id: 'actions', label: 'Corporate Actions', Icon: FileText },
  { id: 'ownership', label: 'Ownership', Icon: Users },
];

export default function CompaniesPage() {
  const { data: session } = useSession();
  const [instruments, setInstruments] = useState<Instrument[]>([]);
  const [selected, setSelected] = useState<string>('BBCA');
  const [search, setSearch] = useState('');
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('profile');
  const [profile, setProfile] = useState<StockProfile | null>(null);
  const [loading, setLoading] = useState(false);

  const authHeader = useCallback((): Record<string, string> => {
    const token = (session as { accessToken?: string } | null)?.accessToken;
    return token ? { Authorization: `Bearer ${token}` } : {};
  }, [session]);

  // Load instrument list
  useEffect(() => {
    if (!session) return;
    fetch('/api/v1/stocks/', { headers: authHeader() })
      .then(r => r.json())
      .then(setInstruments)
      .catch(() => {});
  }, [session, authHeader]);

  // Load profile when symbol changes
  useEffect(() => {
    if (!selected || !session) return;
    setLoading(true);
    fetch(`/api/v1/stocks/${selected}`, { headers: authHeader() })
      .then(r => r.json())
      .then((data: StockProfile) => { setProfile(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, [selected, session, authHeader]);

  const filtered = instruments.filter(i =>
    i.symbol.includes(search.toUpperCase()) ||
    i.name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="flex w-full flex-1 flex-col gap-2 p-2 md:p-3">
      {/* Header with dropdown selector */}
      <div className="card-base" style={{ padding: '12px 16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
          <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
            Company
          </span>
          {/* Dropdown */}
          <div style={{ position: 'relative' }}>
            <button
              onClick={() => setDropdownOpen(o => !o)}
              style={{
                display: 'flex', alignItems: 'center', gap: 8,
                padding: '6px 12px', borderRadius: 6, fontSize: 13, fontWeight: 600,
                border: '1px solid var(--color-border)',
                background: 'var(--color-bg-card)',
                color: 'var(--color-text-primary)',
                cursor: 'pointer', minWidth: 280,
                justifyContent: 'space-between',
              }}
            >
              <span>{selected} — {instruments.find(i => i.symbol === selected)?.name ?? '…'}</span>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="6 9 12 15 18 9" /></svg>
            </button>
            {dropdownOpen && (
              <div style={{
                position: 'absolute', top: '100%', left: 0, zIndex: 50,
                background: 'var(--color-bg-card)',
                border: '1px solid var(--color-border)',
                borderRadius: 8, boxShadow: '0 4px 16px rgba(0,0,0,0.12)',
                width: 320, maxHeight: 320, overflow: 'hidden',
                display: 'flex', flexDirection: 'column',
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
                      onClick={() => { setSelected(i.symbol); setDropdownOpen(false); setSearch(''); }}
                      style={{
                        display: 'flex', alignItems: 'center', gap: 10,
                        width: '100%', padding: '8px 12px', textAlign: 'left',
                        background: i.symbol === selected ? 'rgba(0,87,168,0.06)' : 'transparent',
                        border: 'none', cursor: 'pointer', fontSize: 12,
                        color: 'var(--color-text-primary)',
                        borderBottom: '1px solid var(--color-border-subtle)',
                      }}
                    >
                      <span style={{ fontWeight: 700, color: 'var(--color-blue-primary)', minWidth: 50, fontFamily: 'monospace' }}>{i.symbol}</span>
                      <span style={{ color: 'var(--color-text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{i.name}</span>
                      {i.symbol === selected && (
                        <svg style={{ marginLeft: 'auto', flexShrink: 0 }} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--color-blue-primary)" strokeWidth="2.5"><polyline points="20 6 9 17 4 12" /></svg>
                      )}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
          {profile && (
            <div style={{ display: 'flex', gap: 16, marginLeft: 'auto', alignItems: 'center' }}>
              <div>
                <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--color-text-primary)', fontFamily: 'monospace' }}>
                  {fmtPrice(profile.last_price)}
                </div>
                <div style={{ fontSize: 10, color: 'var(--color-text-muted)' }}>IDR / share</div>
              </div>
              <div style={{ width: 1, height: 32, background: 'var(--color-border)' }} />
              <div>
                <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-text-primary)' }}>{fmtMktCap(profile.market_cap)}</div>
                <div style={{ fontSize: 10, color: 'var(--color-text-muted)' }}>Market Cap</div>
              </div>
              <div style={{ width: 1, height: 32, background: 'var(--color-border)' }} />
              <div>
                <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-text-primary)' }}>{fmtShares(profile.shares_outstanding)}</div>
                <div style={{ fontSize: 10, color: 'var(--color-text-muted)' }}>Shares Outstanding</div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 2, borderBottom: '1px solid var(--color-border)' }}>
        {TABS.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '8px 14px', fontSize: 12, fontWeight: activeTab === tab.id ? 700 : 500,
              color: activeTab === tab.id ? 'var(--color-blue-primary)' : 'var(--color-text-secondary)',
              background: 'transparent', border: 'none', cursor: 'pointer',
              borderBottom: activeTab === tab.id ? '2px solid var(--color-blue-primary)' : '2px solid transparent',
              marginBottom: -1,
            }}
          >
            <tab.Icon size={13} />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {loading ? (
        <div className="card-base" style={{ padding: 40, textAlign: 'center', color: 'var(--color-text-muted)', fontSize: 13 }}>
          Loading {selected}…
        </div>
      ) : profile && activeTab === 'profile' ? (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
          {/* Company Overview */}
          <div className="card-base" style={{ padding: '14px 16px' }}>
            <p className="label-caps" style={{ marginBottom: 12 }}>Company Overview</p>
            <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
              <tbody>
                {[
                  ['Symbol', profile.symbol],
                  ['Full Name', profile.name],
                  ['Exchange', profile.exchange],
                  ['Sector', profile.sector ?? '—'],
                  ['Industry', profile.industry ?? '—'],
                  ['Listing Date', profile.listing_date ?? '—'],
                  ['LQ45 Member', profile.is_lq45 ? 'Yes' : 'No'],
                ].map(([k, v]) => (
                  <tr key={k} style={{ borderBottom: '1px solid var(--color-border-subtle)' }}>
                    <td style={{ padding: '7px 0', color: 'var(--color-text-muted)', width: '40%' }}>{k}</td>
                    <td style={{ padding: '7px 0', fontWeight: 600, color: 'var(--color-text-primary)' }}>{v}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {/* Business Description */}
          <div className="card-base" style={{ padding: '14px 16px' }}>
            <p className="label-caps" style={{ marginBottom: 12 }}>Business Description</p>
            <p style={{ fontSize: 12, color: 'var(--color-text-secondary)', lineHeight: 1.6 }}>
              {profile.description ?? 'No description available from data provider.'}
            </p>
          </div>
        </div>
      ) : activeTab === 'index' ? (
        <div className="card-base" style={{ padding: '14px 16px' }}>
          <p className="label-caps" style={{ marginBottom: 12 }}>Index Composition</p>
          <p style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>
            Index constituent data requires ingestion pipeline. Coming in next release.
          </p>
        </div>
      ) : activeTab === 'actions' ? (
        <div className="card-base" style={{ padding: '14px 16px' }}>
          <p className="label-caps" style={{ marginBottom: 12 }}>Corporate Actions</p>
          <p style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>
            Corporate actions data requires ingestion pipeline. Coming in next release.
          </p>
        </div>
      ) : activeTab === 'ownership' ? (
        <div className="card-base" style={{ padding: '14px 16px' }}>
          <p className="label-caps" style={{ marginBottom: 12 }}>Ownership Structure</p>
          <p style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>
            Ownership data requires ingestion pipeline. Coming in next release.
          </p>
        </div>
      ) : null}
    </div>
  );
}
