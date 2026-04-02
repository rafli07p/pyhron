export interface ShortcutDef {
  key: string;
  meta?: boolean;
  shift?: boolean;
  label: string;
}

export const SHORTCUTS = {
  commandPalette: { key: 'k', meta: true, label: 'Command palette' },
  search: { key: '/', label: 'Focus search' },
  notifications: { key: 'n', meta: true, label: 'Toggle notifications' },
  toggleSidebar: { key: 'b', meta: true, label: 'Toggle sidebar' },
  toggleTheme: { key: 'd', meta: true, shift: true, label: 'Toggle dark mode' },

  gotoDashboard: { key: 'g d', label: 'Go to Dashboard' },
  gotoMarkets: { key: 'g m', label: 'Go to Markets' },
  gotoPortfolio: { key: 'g p', label: 'Go to Portfolio' },
  gotoStrategies: { key: 'g s', label: 'Go to Strategies' },
  gotoResearch: { key: 'g r', label: 'Go to Research' },
  gotoRisk: { key: 'g k', label: 'Go to Risk' },
  gotoSettings: { key: 'g ,', label: 'Go to Settings' },

  quickBuy: { key: 'b', label: 'Quick buy' },
  quickSell: { key: 's', label: 'Quick sell' },
  cancelOrder: { key: 'x', label: 'Cancel selected order' },
  addToWatchlist: { key: 'w', label: 'Add to watchlist' },

  tableUp: { key: 'ArrowUp', label: 'Previous row' },
  tableDown: { key: 'ArrowDown', label: 'Next row' },
  tableSelect: { key: 'Enter', label: 'Open selected' },

  showShortcuts: { key: '?', label: 'Show keyboard shortcuts' },
} as const satisfies Record<string, ShortcutDef>;
