/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        voidonyx: {
          orange: '#FF5C00',
          darkOrange: '#E04D00',
          cream: '#FAF8F5',
          card: '#FFFFFF',
          slate: '#0F172A',
          muted: '#64748B',
          border: '#EAE5DC',
        }
      },
      fontFamily: {
        sans: ['Plus Jakarta Sans', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      }
    },
  },
  plugins: [],
}
