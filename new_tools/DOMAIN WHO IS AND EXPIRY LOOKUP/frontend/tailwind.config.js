/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          amber: '#f59e0b',
          amberDark: '#d97706',
          red: '#E11D48',
          redDark: '#BE123C',
          bg: '#F8FAFC',
          card: '#FFFFFF',
          border: '#E2E8F0',
          text: '#0F172A',
          muted: '#64748B',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'ui-monospace', 'monospace'],
      },
      boxShadow: {
        'brand-glow': '0 4px 12px rgba(245, 158, 11, 0.25)',
        'red-glow': '0 4px 14px rgba(225, 29, 72, 0.25)',
        'card': '0 4px 20px -2px rgba(15, 23, 42, 0.04), 0 2px 6px -1px rgba(15, 23, 42, 0.02)',
      },
    },
  },
  plugins: [],
};
