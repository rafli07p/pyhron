'use client';

import { useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { ChevronLeft, ChevronRight, BarChart2, GitBranch, FileText, Users, TrendingUp } from 'lucide-react';

const NAV_ITEMS = [
  { label: 'Index Composition Viewer', path: '/companies/index-composition', Icon: GitBranch },
  { label: 'Corporate Actions', path: '/companies/corporate-actions', Icon: FileText },
  { label: 'Financial Highlights', path: '/companies/financials', Icon: BarChart2 },
  { label: 'Ownership Structure', path: '/companies/ownership', Icon: Users },
  { label: 'Peer Comparison', path: '/companies/peers', Icon: TrendingUp },
];

export default function CompaniesLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>
      {/* Secondary Sidebar */}
      <aside style={{
        width: collapsed ? 0 : 220,
        minWidth: collapsed ? 0 : 220,
        borderRight: collapsed ? 'none' : '1px solid var(--color-border)',
        background: '#fff',
        display: 'flex',
        flexDirection: 'column',
        transition: 'width 0.2s ease, min-width 0.2s ease',
        overflow: 'hidden',
        position: 'relative',
      }}>
        {!collapsed && (
          <>
            {/* Section header with collapse button */}
            <div style={{
              padding: '12px 16px 10px',
              borderBottom: '1px solid var(--color-border)',
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            }}>
              <span style={{
                fontSize: 10, fontWeight: 700, letterSpacing: '0.08em',
                textTransform: 'uppercase', color: 'var(--color-text-muted)',
              }}>
                Company Insights
              </span>
              <button
                onClick={() => setCollapsed(true)}
                style={{
                  width: 20, height: 20, borderRadius: 3,
                  background: 'transparent', border: 'none',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  cursor: 'pointer',
                }}
                aria-label="Collapse sidebar"
              >
                <ChevronLeft size={13} style={{ color: 'var(--color-text-muted)' }} />
              </button>
            </div>

            {/* Nav items */}
            <nav style={{ flex: 1, overflowY: 'auto', padding: '6px 0', display: 'flex', flexDirection: 'column', gap: 2 }}>
              {NAV_ITEMS.map(item => {
                const active = pathname === item.path;
                return (
                  <button
                    key={item.path}
                    onClick={() => router.push(item.path)}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 8,
                      width: '100%', padding: '9px 16px',
                      background: active ? 'rgba(0,87,168,0.08)' : 'transparent',
                      border: 'none',
                      borderLeft: active ? '3px solid var(--color-blue-primary)' : '3px solid transparent',
                      cursor: 'pointer', textAlign: 'left',
                      fontSize: 12,
                      fontWeight: active ? 600 : 400,
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
      <div style={{ flex: 1, overflow: 'auto', display: 'flex', flexDirection: 'column', position: 'relative' }}>
        {/* Collapsed expand button — shown only when sidebar is collapsed, mimics MSCI ONE */}
        {collapsed && (
          <button
            onClick={() => setCollapsed(false)}
            style={{
              position: 'absolute', top: 10, left: 8, zIndex: 20,
              width: 24, height: 24, borderRadius: 4,
              background: '#fff', border: '1px solid var(--color-border)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              cursor: 'pointer',
              boxShadow: '0 1px 4px rgba(0,0,0,0.08)',
            }}
            aria-label="Expand sidebar"
          >
            <ChevronRight size={13} style={{ color: 'var(--color-text-muted)' }} />
          </button>
        )}

        {/* Page content */}
        <div style={{ flex: 1, overflow: 'auto' }}>
          {children}
        </div>
      </div>
    </div>
  );
}
