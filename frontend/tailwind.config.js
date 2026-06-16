/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        surface: {
          900: '#0a0b0f',
          800: '#12131a',
          700: '#1a1c26',
          600: '#242733',
        },
        accent: {
          green: '#00e5a0',
          red: '#ff3b5c',
          amber: '#ffb020',
          blue: '#3b82f6',
          cyan: '#06d6d0',
        }
      },
      fontFamily: {
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'monospace'],
        display: ['"IBM Plex Sans"', 'system-ui', 'sans-serif'],
        body: ['"IBM Plex Sans"', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
