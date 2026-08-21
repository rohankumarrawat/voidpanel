/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        /* ── VoidOnyx Design System tokens ────────────── */
        ox: {
          navy:       '#0f172a',
          'navy-lt':  '#1e293b',
          blue:       '#2563eb',
          'blue-mid': '#3b82f6',
          'blue-lt':  '#60a5fa',
          indigo:     '#4f46e5',
          teal:       '#0ea5e9',
          bg:         '#f8fafc',
          'bg-alt':   '#f1f5f9',
          surface:    '#ffffff',
          muted:      '#64748b',
          faint:      '#94a3b8',
        },
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      backgroundImage: {
        'ox-brand': 'linear-gradient(135deg, #2563eb 0%, #4f46e5 100%)',
        'ox-blue':  'linear-gradient(135deg, #0ea5e9 0%, #2563eb 100%)',
        'ox-hero':  'linear-gradient(160deg, #f0f7ff 0%, #f8fafc 50%, #eff2ff 100%)',
      },
      boxShadow: {
        'ox-sm': '0 1px 2px rgba(15,23,42,0.06)',
        'ox-md': '0 4px 12px rgba(15,23,42,0.08), 0 1px 3px rgba(15,23,42,0.05)',
        'ox-lg': '0 12px 36px rgba(15,23,42,0.10), 0 4px 12px rgba(15,23,42,0.06)',
        'ox-xl': '0 24px 60px rgba(15,23,42,0.12), 0 8px 20px rgba(15,23,42,0.08)',
        'ox-blue': '0 4px 14px rgba(37,99,235,0.30)',
      },
      borderRadius: {
        'ox-sm': '8px',
        'ox-md': '12px',
        'ox-lg': '20px',
        'ox-xl': '28px',
      },
    },
  },
  plugins: [],
}
