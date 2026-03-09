export const typographyScale = {
  display: {
    fontSize: '2rem',
    lineHeight: '2.5rem',
    fontWeight: 700,
    fontFamily: 'sans',
    letterSpacing: '-0.02em',
  },
  heading1: {
    fontSize: '1.5rem',
    lineHeight: '2rem',
    fontWeight: 600,
    fontFamily: 'sans',
    letterSpacing: '-0.01em',
  },
  heading2: {
    fontSize: '1.125rem',
    lineHeight: '1.5rem',
    fontWeight: 600,
    fontFamily: 'sans',
  },
  heading3: {
    fontSize: '0.875rem',
    lineHeight: '1.25rem',
    fontWeight: 600,
    fontFamily: 'sans',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.05em',
  },
  body: {
    fontSize: '0.875rem',
    lineHeight: '1.25rem',
    fontWeight: 400,
    fontFamily: 'sans',
  },
  bodySmall: {
    fontSize: '0.75rem',
    lineHeight: '1rem',
    fontWeight: 400,
    fontFamily: 'sans',
  },
  caption: {
    fontSize: '0.625rem',
    lineHeight: '0.875rem',
    fontWeight: 400,
    fontFamily: 'sans',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.08em',
  },
  /** Monospace for numbers, tickers, prices */
  numeric: {
    fontSize: '0.875rem',
    lineHeight: '1.25rem',
    fontWeight: 500,
    fontFamily: 'mono',
    fontVariantNumeric: 'tabular-nums',
  },
  numericLarge: {
    fontSize: '1.25rem',
    lineHeight: '1.75rem',
    fontWeight: 600,
    fontFamily: 'mono',
    fontVariantNumeric: 'tabular-nums',
  },
  numericSmall: {
    fontSize: '0.75rem',
    lineHeight: '1rem',
    fontWeight: 500,
    fontFamily: 'mono',
    fontVariantNumeric: 'tabular-nums',
  },
  ticker: {
    fontSize: '0.75rem',
    lineHeight: '1rem',
    fontWeight: 700,
    fontFamily: 'mono',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.04em',
  },
} as const;

/** Format a number with Indonesian locale and fixed decimals */
export function formatNumber(value: number, decimals = 0): string {
  return value.toLocaleString('id-ID', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

/** Format price in IDR */
export function formatIDR(value: number): string {
  if (value >= 1_000_000_000_000) {
    return `Rp${(value / 1_000_000_000_000).toFixed(1)}T`;
  }
  if (value >= 1_000_000_000) {
    return `Rp${(value / 1_000_000_000).toFixed(1)}B`;
  }
  if (value >= 1_000_000) {
    return `Rp${(value / 1_000_000).toFixed(1)}M`;
  }
  return `Rp${formatNumber(value)}`;
}

/** Format percentage */
export function formatPercent(value: number, decimals = 2): string {
  const sign = value > 0 ? '+' : '';
  return `${sign}${value.toFixed(decimals)}%`;
}

export type TypographyScale = typeof typographyScale;
