import type { Config } from 'tailwindcss';

export default {
  darkMode: 'class',
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          blue: '#0057A8',
          blueDark: '#003D7A',
          blueSoft: '#EBF3FC',
        },
        surface: {
          0: 'var(--surface-0)',
          1: 'var(--surface-1)',
          2: 'var(--surface-2)',
          3: 'var(--surface-3)',
          4: 'var(--surface-4)',
          page: '#F5F7FA',
          card: '#FFFFFF',
        },
        border: {
          DEFAULT: '#E8ECF0',
          subtle: '#F0F4F8',
        },
        text: {
          primary: '#1A1A2E',
          secondary: '#5A6A7A',
          muted: '#8A9BB0',
        },
        accent: {
          50: 'var(--accent-50)',
          100: 'var(--accent-100)',
          500: 'var(--accent-500)',
          600: 'var(--accent-600)',
          700: 'var(--accent-700)',
        },
        positive: {
          DEFAULT: '#00875A',
          muted: 'var(--positive-muted)',
          bg: '#E3F5EE',
        },
        negative: {
          DEFAULT: '#D92D20',
          muted: 'var(--negative-muted)',
          bg: '#FDECEA',
        },
        warning: {
          DEFAULT: 'var(--warning)',
          muted: 'var(--warning-muted)',
        },
        info: {
          DEFAULT: 'var(--info)',
          muted: 'var(--info-muted)',
        },
      },
      fontFamily: {
        sans: ['var(--font-sans)', 'system-ui', 'sans-serif'],
        mono: ['var(--font-mono)', 'Consolas', 'monospace'],
      },
      maxWidth: {
        content: '1440px',
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
} satisfies Config;
