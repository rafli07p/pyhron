'use client';

import { TopNav } from './TopNav';
import { Sidebar } from './Sidebar';
import { CommandPalette } from './CommandPalette';

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen flex-col">
      <TopNav />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <main id="main-content" className="flex-1 overflow-y-auto bg-[var(--surface-0)] p-4 lg:p-6">
          {children}
        </main>
      </div>
      <CommandPalette />
    </div>
  );
}
