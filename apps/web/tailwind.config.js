/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        bloomberg: {
          bg: {
            primary: '#0a0a0a',
            secondary: '#121212',
            tertiary: '#1a1a1a',
            elevated: '#242424',
          },
          accent: '#ff6600',
          'accent-hover': '#ff8533',
          green: '#00c853',
          red: '#ff1744',
          yellow: '#ffd600',
          blue: '#2979ff',
          text: {
            primary: '#e0e0e0',
            secondary: '#9e9e9e',
            muted: '#616161',
          },
          border: '#2a2a2a',
          'border-hover': '#3a3a3a',
        },
      },
      fontFamily: {
        mono: [
          'JetBrains Mono',
          'Fira Code',
          'SF Mono',
          'Consolas',
          'Liberation Mono',
          'Menlo',
          'monospace',
        ],
        sans: [
          'Inter',
          '-apple-system',
          'BlinkMacSystemFont',
          'Segoe UI',
          'sans-serif',
        ],
      },
      fontSize: {
        'xxs': '0.625rem',
      },
    },
  },
  plugins: [],
};
