'use client';

import { TerminalTopBar } from '@/components/layout/TerminalTopBar';
import { Sidebar } from './Sidebar';
import { CommandPalette } from './CommandPalette';

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen flex-col bg-[#1b2a3d]">
      <TerminalTopBar />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <main id="main-content" className="flex-1 overflow-y-auto bg-[#f3f4f6]">
          {children}
        </main>
      </div>
      <CommandPalette />
    </div>
  );
}
