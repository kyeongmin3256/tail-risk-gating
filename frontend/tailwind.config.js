/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        paper: '#F3F1EC',
        ink: '#1F4B6E',
        'ink-deep': '#1A1A1A',
        muted: '#5C5A55',
        line: '#D9D4C8',
        up: '#2F6B4F',
        down: '#9B3A3A',
        warn: '#8A6A1F',
      },
      fontFamily: {
        display: ['"Source Serif 4"', 'Georgia', 'serif'],
        sans: ['"IBM Plex Sans"', 'system-ui', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'monospace'],
      },
      letterSpacing: {
        label: '0.14em',
      },
    },
  },
  plugins: [],
}
