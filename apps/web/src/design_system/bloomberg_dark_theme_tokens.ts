export const themeTokens = {
  colors: {
    bg: {
      primary: '#0a0a0a',
      secondary: '#121212',
      tertiary: '#1a1a1a',
      elevated: '#242424',
      overlay: 'rgba(0, 0, 0, 0.7)',
    },
    accent: {
      orange: '#ff6600',
      orangeHover: '#ff8533',
      orangeMuted: 'rgba(255, 102, 0, 0.15)',
    },
    semantic: {
      positive: '#00c853',
      negative: '#ff1744',
      warning: '#ffd600',
      info: '#2979ff',
      positiveBg: 'rgba(0, 200, 83, 0.1)',
      negativeBg: 'rgba(255, 23, 68, 0.1)',
    },
    text: {
      primary: '#e0e0e0',
      secondary: '#9e9e9e',
      muted: '#616161',
      inverse: '#0a0a0a',
    },
    border: {
      default: '#2a2a2a',
      hover: '#3a3a3a',
      focus: '#ff6600',
    },
  },
  fonts: {
    mono: "'JetBrains Mono', 'Fira Code', 'SF Mono', 'Consolas', 'Liberation Mono', 'Menlo', monospace",
    sans: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
  },
  spacing: {
    xs: '0.25rem',
    sm: '0.5rem',
    md: '0.75rem',
    lg: '1rem',
    xl: '1.5rem',
    xxl: '2rem',
  },
  radii: {
    sm: '0.25rem',
    md: '0.375rem',
    lg: '0.5rem',
  },
} as const;

/** Flat alias for inline style usage */
export const theme = themeTokens.colors;

export type ThemeTokens = typeof themeTokens;
