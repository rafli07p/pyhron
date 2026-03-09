/** Dense layout utility classes for financial data displays */
export const layoutTokens = {
  /** Compact row height for data tables */
  denseRowHeight: '28px',
  /** Standard row height */
  standardRowHeight: '36px',

  /** Grid configurations for dashboard layouts */
  grid: {
    /** 4-column dense grid */
    quad: 'grid grid-cols-4 gap-2',
    /** 3-column layout */
    triple: 'grid grid-cols-3 gap-3',
    /** 2-column split */
    split: 'grid grid-cols-2 gap-3',
    /** Sidebar + main content */
    sidebar: 'grid grid-cols-[320px_1fr] gap-3',
    /** Responsive 4-col grid */
    responsive: 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3',
  },

  /** Panel styles */
  panel: {
    base: 'bg-bloomberg-bg-secondary border border-bloomberg-border rounded-md',
    header: 'px-3 py-2 border-b border-bloomberg-border flex items-center justify-between',
    body: 'p-3',
    bodyDense: 'p-2',
  },

  /** Data density patterns */
  density: {
    /** Compact key-value pair */
    kvPair: 'flex justify-between items-center py-1 text-xs',
    /** Dense stat block */
    statBlock: 'flex flex-col gap-0.5',
    /** Inline metric */
    inlineMetric: 'inline-flex items-center gap-1 font-mono text-xs',
  },
} as const;

/** Common Tailwind class combinations for dense financial layouts */
export const denseTableClasses = {
  table: 'w-full text-xs font-mono',
  thead: 'text-bloomberg-text-muted text-xxs uppercase tracking-wider',
  th: 'px-2 py-1.5 text-right first:text-left font-medium border-b border-bloomberg-border',
  tr: 'border-b border-bloomberg-border/50 hover:bg-bloomberg-bg-tertiary transition-colors',
  td: 'px-2 py-1 text-right first:text-left tabular-nums',
  tdTicker: 'px-2 py-1 text-left font-bold text-bloomberg-accent',
} as const;

export type LayoutTokens = typeof layoutTokens;
