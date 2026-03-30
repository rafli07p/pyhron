import type { Config } from 'tailwindcss';

export default {
  darkMode: 'class',
  content: ['./src/**/*.{ts,tsx,mdx}'],
  theme: {
    extend: {
      colors: {
        primary: {
          500: '#1a3a6b',
          600: '#152e56',
          700: '#102341',
          800: '#0b172c',
          900: '#060c17',
        },
        accent: { 500: '#00d4aa', 600: '#00b894', 700: '#009b7d' },
        positive: '#10b981',
        negative: '#ef4444',
        warning: '#f59e0b',
      },
      fontFamily: {
        display: ['DM Serif Display', 'serif'],
        body: ['Satoshi', 'General Sans', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      maxWidth: { content: '1440px' },
    },
  },
  plugins: [require('tailwindcss-animate')],
} satisfies Config;
