'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { signOut } from 'next-auth/react';
import { LayoutDashboard, Briefcase, Cpu, Database, Key, Settings, ChevronLeft, LogOut } from 'lucide-react';

const sidebarItems = [
  { label: 'Overview', href: '/dashboard/overview', icon: LayoutDashboard },
  { label: 'Portfolio', href: '/dashboard/portfolio', icon: Briefcase },
  { label: 'Strategies', href: '/dashboard/strategies', icon: Cpu },
  { label: 'Data Explorer', href: '/dashboard/data-explorer', icon: Database },
  { label: 'API Keys', href: '/dashboard/api-keys', icon: Key },
  { label: 'Settings', href: '/dashboard/settings', icon: Settings },
];

export function DashboardShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="flex min-h-[calc(100vh-64px)]">
      <aside className={`border-r border-border bg-bg-secondary transition-all ${collapsed ? 'w-16' : 'w-56'}`}>
        <div className="flex h-full flex-col p-3">
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="mb-4 flex items-center justify-center rounded-md p-2 text-text-muted hover:bg-bg-tertiary"
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            <ChevronLeft className={`h-4 w-4 transition-transform ${collapsed ? 'rotate-180' : ''}`} />
          </button>
          <nav className="flex-1 space-y-1">
            {sidebarItems.map((item) => {
              const isActive = pathname === item.href || pathname?.startsWith(item.href + '/');
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors ${
                    isActive
                      ? 'bg-accent-500/10 text-accent-500 font-medium'
                      : 'text-text-secondary hover:bg-bg-tertiary hover:text-text-primary'
                  }`}
                  title={collapsed ? item.label : undefined}
                >
                  <item.icon className="h-4 w-4 flex-shrink-0" />
                  {!collapsed && <span>{item.label}</span>}
                </Link>
              );
            })}
          </nav>
          <div className="mt-auto pt-4 border-t border-border">
            <button
              onClick={() => signOut({ callbackUrl: '/' })}
              className="flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm text-text-secondary hover:bg-bg-tertiary hover:text-text-primary"
            >
              <LogOut className="h-4 w-4 flex-shrink-0" />
              {!collapsed && <span>Sign out</span>}
            </button>
            <Link
              href="/solutions/live-terminal"
              className="mt-2 flex items-center gap-3 rounded-md border border-border px-3 py-2 text-xs text-text-muted hover:border-accent-500 hover:text-accent-500 transition-colors"
            >
              {!collapsed ? 'Open Trading Terminal' : 'T'}
            </Link>
          </div>
        </div>
      </aside>
      <div className="flex-1 overflow-auto p-6">{children}</div>
    </div>
  );
}
