import type { Config } from 'tailwindcss'

const config: Config = {
  // Dark mode: [data-theme="dark"] attribute on <html>
  darkMode: ['class', '[data-theme="dark"]'],

  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './context/**/*.{js,ts,jsx,tsx,mdx}',
    './hooks/**/*.{js,ts,jsx,tsx,mdx}',
    './lib/**/*.{js,ts,jsx,tsx,mdx}',
  ],

  theme: {
    extend: {
      // ── Brand Colors ────────────────────────────────────────
      colors: {
        lumina: {
          50:  '#f0effe',
          100: '#e2dffe',
          200: '#c9c2fd',
          300: '#a99afb',
          400: '#8670f8',
          500: '#6C63FF', // ← Primary Brand
          600: '#5a4ef7',
          700: '#4a3de3',
          800: '#3c31be',
          900: '#332c99',
          950: '#1e1a63',
        },
        teal: {
          300: '#00e5e6',
          400: '#00D2D3',
          500: '#00babb',
        },
      },

      // ── Typography ───────────────────────────────────────────
      fontFamily: {
        sans: ['var(--font-sans)', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['var(--font-mono)', 'Fira Code', 'Menlo', 'monospace'],
      },

      // ── Animations ───────────────────────────────────────────
      animation: {
        'fade-up':        'fadeUp 0.45s cubic-bezier(0.16, 1, 0.3, 1) both',
        'scale-in':       'scaleIn 0.3s cubic-bezier(0.16, 1, 0.3, 1) both',
        'shimmer':        'shimmer 1.8s linear infinite',
        'pulse-glow':     'pulseGlow 2.5s ease-in-out infinite',
        'spin-slow':      'spinSlow 3s linear infinite',
        'float':          'float 3.5s ease-in-out infinite',
        'slide-in-left':  'slideInLeft 0.35s ease-out both',
        'gradient-shift': 'gradientShift 4s ease infinite',
        'border-pulse':   'borderPulse 2s ease-in-out infinite',
        'typing-dot':     'typingDot 1.4s ease-in-out infinite',
      },

      keyframes: {
        fadeUp: {
          '0%':   { opacity: '0', transform: 'translateY(18px) scale(0.98)' },
          '100%': { opacity: '1', transform: 'translateY(0) scale(1)' },
        },
        scaleIn: {
          '0%':   { opacity: '0', transform: 'scale(0.92)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        shimmer: {
          '0%':   { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition:  '200% 0' },
        },
        pulseGlow: {
          '0%, 100%': { boxShadow: '0 0 0 0 rgba(108,99,255,0)' },
          '50%':       { boxShadow: '0 0 20px 6px rgba(108,99,255,0.18)' },
        },
        spinSlow: {
          from: { transform: 'rotate(0deg)' },
          to:   { transform: 'rotate(360deg)' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%':       { transform: 'translateY(-10px)' },
        },
        slideInLeft: {
          '0%':   { opacity: '0', transform: 'translateX(-16px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
        gradientShift: {
          '0%, 100%': { backgroundPosition: '0% 50%' },
          '50%':       { backgroundPosition: '100% 50%' },
        },
        borderPulse: {
          '0%, 100%': { borderColor: 'rgb(108 99 255 / 0.18)' },
          '50%':       { borderColor: 'rgb(108 99 255 / 0.55)' },
        },
        typingDot: {
          '0%, 55%, 100%': { transform: 'translateY(0)',    opacity: '0.35' },
          '28%':            { transform: 'translateY(-7px)', opacity: '1' },
        },
      },

      // ── Shadows ──────────────────────────────────────────────
      boxShadow: {
        'glass':       '0 8px 32px -4px rgba(0,0,0,0.10), inset 0 1px 0 rgba(255,255,255,0.05)',
        'glass-dark':  '0 8px 32px -4px rgba(0,0,0,0.30), inset 0 1px 0 rgba(255,255,255,0.04)',
        'lumina':      '0 4px 24px rgba(108,99,255,0.22)',
        'lumina-lg':   '0 8px 40px rgba(108,99,255,0.32)',
        'card':        '0 1px 2px rgba(15,23,42,0.05), 0 4px 12px rgba(15,23,42,0.04)',
        'card-hover':  '0 4px 20px rgba(15,23,42,0.08)',
        'inner-white': 'inset 0 1px 0 rgba(255,255,255,0.06)',
      },

      // ── Background Images ────────────────────────────────────
      backgroundImage: {
        'lumina-gradient':  'linear-gradient(135deg, #6C63FF 0%, #00D2D3 100%)',
        'lumina-soft':      'linear-gradient(135deg, rgba(108,99,255,0.12) 0%, rgba(0,210,211,0.06) 100%)',
        'shimmer-gradient': 'linear-gradient(90deg, transparent 25%, rgba(255,255,255,0.05) 50%, transparent 75%)',
        'dark-noise':       'url("data:image/svg+xml,%3Csvg viewBox=\'0 0 256 256\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cfilter id=\'noise\'%3E%3CfeTurbulence type=\'fractalNoise\' baseFrequency=\'0.9\' numOctaves=\'4\' stitchTiles=\'stitch\'/%3E%3C/filter%3E%3Crect width=\'100%25\' height=\'100%25\' filter=\'url(%23noise)\' opacity=\'0.03\'/%3E%3C/svg%3E")',
      },

      // ── Border Radius ────────────────────────────────────────
      borderRadius: {
        '4xl': '2rem',
        '5xl': '2.5rem',
      },

      // ── Transition Timing ────────────────────────────────────
      transitionTimingFunction: {
        'spring': 'cubic-bezier(0.34, 1.56, 0.64, 1)',
        'snappy': 'cubic-bezier(0.16, 1, 0.3, 1)',
      },

      // ── Z-index ──────────────────────────────────────────────
      zIndex: {
        '60': '60',
        '70': '70',
        '80': '80',
      },

      // ── Custom Screens ───────────────────────────────────────
      screens: {
        'xs': '475px',
        '3xl': '1920px',
      },
    },
  },
  plugins: [],
}

export default config
