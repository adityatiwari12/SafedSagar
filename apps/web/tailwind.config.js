/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ivory: {
          DEFAULT: '#F7F3EA',
          deep: '#EDE6D6',
        },
        forest: {
          DEFAULT: '#0A3D2E',
          mid: '#0F5C45',
          leaf: '#1A7A58',
        },
        saffron: {
          DEFAULT: '#FF671F',
          soft: '#FF9933',
          deep: '#D35400',
        },
        gold: {
          DEFAULT: '#B08D57',
          soft: '#E2D0A8',
        },
        navy: '#0B1F3A',
        charcoal: '#1C2421',
        paper: '#F7F3EA',
        ink: {
          DEFAULT: '#1C2421',
          muted: '#4A5550',
          faint: '#6E7873',
        },
        surface: {
          DEFAULT: '#ffffff',
          muted: '#F7F3EA',
          border: '#DDD5C4',
        },
        line: '#DDD5C4',
        ayush: {
          DEFAULT: '#0F5C45',
          bright: '#138808',
          soft: '#E8F2ED',
        },
        primary: {
          DEFAULT: '#FF671F',
          dark: '#D35400',
          deeper: '#A04000',
        },
        indiaGreen: '#138808',
        brass: {
          DEFAULT: '#B08D57',
          soft: '#E2D0A8',
        },
      },
      fontFamily: {
        sans: ['"Noto Sans"', 'system-ui', 'sans-serif'],
        display: ['"Noto Sans"', 'system-ui', 'sans-serif'],
        hindi: ['"Noto Sans Devanagari"', '"Noto Sans"', 'sans-serif'],
      },
      maxWidth: {
        portal: '94rem',
      },
      boxShadow: {
        panel: '0 1px 0 rgba(28, 36, 33, 0.06)',
        lift: '0 24px 60px rgba(10, 61, 46, 0.22)',
        float: '0 12px 32px rgba(10, 61, 46, 0.14)',
      },
      fontSize: {
        hero: ['clamp(3rem, 7vw, 5.5rem)', { lineHeight: '0.95', fontWeight: '800' }],
        section: ['clamp(2rem, 4vw, 3.75rem)', { lineHeight: '1.05', fontWeight: '700' }],
      },
    },
  },
  plugins: [],
}
