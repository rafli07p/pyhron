'use client';

import { TerminalTopBar } from '@/components/layout/TerminalTopBar';
import { Sidebar } from './Sidebar';
import { CommandPalette } from './CommandPalette';

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen flex-col">
      <TerminalTopBar />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <main id="main-content" className="flex-1 overflow-y-auto bg-white">
          {children}
        </main>
      </div>
      <CommandPalette />
    </div>
  );
}
