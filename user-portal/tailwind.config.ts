import type { Config } from 'tailwindcss';

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#fcfbf9',
        sidebar: '#fbfbfa',
        card: '#f7f6f3',
        'text-primary': '#37352f',
        'text-secondary': '#787774',
        accent: '#2383e2',
        border: '#e3e2e0',
        hover: '#efefef',
        'accent-teal': '#14b8a6',
        'accent-cobalt': '#2563eb',
        'accent-violet': '#7c3aed',
        teal: '#14b8a6',
        cobalt: '#2563eb',
        violet: '#7c3aed',
        ink: '#1f1d1a',
        'ink-2': '#37352f',
        'ink-3': '#6b6966',
        'ink-4': '#9a9894',
        line: '#e8e6e1',
        'line-2': '#dedcd6',
        amber: '#c2410c',
      },
      keyframes: {
        fadeUp: {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        thoughtIn: {
          '0%': { opacity: '0', transform: 'translateY(6px)', filter: 'blur(4px)' },
          '100%': { opacity: '1', transform: 'translateY(0)', filter: 'blur(0)' },
        },
        ringSpin: {
          '0%': { transform: 'rotate(0deg)' },
          '100%': { transform: 'rotate(360deg)' },
        },
      },
      animation: {
        'fade-up': 'fadeUp 450ms cubic-bezier(.2,.7,.2,1) both',
        'thought-in': 'thoughtIn 550ms cubic-bezier(.2,.7,.2,1) both',
        'ring-spin': 'ringSpin 2400ms linear infinite',
      },
    },
  },
  plugins: [],
} satisfies Config;
