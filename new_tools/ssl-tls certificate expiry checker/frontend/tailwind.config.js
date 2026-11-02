/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        void: {
          950: "#060709",
          900: "#0a0c10",
          850: "#0f1218",
          800: "#141822",
          700: "#1e2638",
          600: "#2a364f",
        },
        cyan: {
          glow: "#00f3ff",
        },
        acid: {
          glow: "#00ff66",
        },
        ruby: {
          glow: "#ff0055",
        },
        amber: {
          glow: "#ffb703",
        },
      },
      fontFamily: {
        mono: ['"JetBrains Mono"', 'Consolas', 'Monaco', 'ui-monospace', 'monospace'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      animation: {
        'pulse-glow': 'pulseGlow 2s infinite ease-in-out',
        'scanline': 'scanline 8s linear infinite',
      },
      keyframes: {
        pulseGlow: {
          '0%, 100%': { opacity: '0.6', filter: 'drop-shadow(0 0 8px rgba(0, 243, 255, 0.4))' },
          '50%': { opacity: '1', filter: 'drop-shadow(0 0 16px rgba(0, 243, 255, 0.8))' },
        },
        scanline: {
          '0%': { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(1000%)' },
        },
      },
    },
  },
  plugins: [],
};
