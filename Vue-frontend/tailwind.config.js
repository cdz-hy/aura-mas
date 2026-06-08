/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        navy: {
          50: '#f0f3f9',
          100: '#d9e0f0',
          200: '#b3c1e0',
          300: '#8da2d1',
          400: '#6783c1',
          500: '#4164b2',
          600: '#34508e',
          700: '#273c6b',
          800: '#1a2847',
          900: '#0d1424',
          950: '#070a12',
        },
        cream: {
          50: '#fefdfb',
          100: '#fdf9f0',
          200: '#faf3e1',
          300: '#f7edd2',
          400: '#f4e7c3',
          500: '#f1e1b4',
          600: '#c4b790',
          700: '#978d6c',
          800: '#6a6348',
          900: '#3d3924',
        },
        sage: {
          50: '#f4f7f4',
          100: '#e0ebe0',
          200: '#c1d7c1',
          300: '#a2c3a2',
          400: '#83af83',
          500: '#649b64',
          600: '#507c50',
          700: '#3c5d3c',
          800: '#283e28',
          900: '#141f14',
        },
      },
      fontFamily: {
        display: ['"Playfair Display"', 'Georgia', 'serif'],
        body: ['"Source Sans 3"', '"Noto Sans SC"', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', '"Fira Code"', 'monospace'],
      },
      boxShadow: {
        'paper': '0 1px 3px rgba(0,0,0,0.08), 0 4px 12px rgba(0,0,0,0.04)',
        'paper-hover': '0 2px 8px rgba(0,0,0,0.12), 0 8px 24px rgba(0,0,0,0.06)',
        'glow': '0 0 20px rgba(65,100,178,0.15)',
      },
      backgroundImage: {
        'paper-texture': "url(\"data:image/svg+xml,%3Csvg width='100' height='100' viewBox='0 0 100 100' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100' height='100' filter='url(%23noise)' opacity='0.03'/%3E%3C/svg%3E\")",
      },
    },
  },
  plugins: [],
}
