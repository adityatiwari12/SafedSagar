/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // UX4G / GOI-aligned tokens
        primary: {
          DEFAULT: '#0d6efd',
          dark: '#0a58ca',
          deeper: '#084298',
        },
        saffron: '#FF9933',
        indiaGreen: '#138808',
        navy: '#0b1f3a',
        surface: {
          DEFAULT: '#ffffff',
          muted: '#f4f6f8',
          border: '#dee2e6',
        },
        ink: {
          DEFAULT: '#212529',
          muted: '#495057',
          faint: '#6c757d',
        },
      },
      fontFamily: {
        sans: ['"Noto Sans"', 'system-ui', 'Segoe UI', 'sans-serif'],
        display: ['"Noto Sans"', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        panel: '0 1px 3px rgba(11, 31, 58, 0.08)',
      },
    },
  },
  plugins: [],
}
