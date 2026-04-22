import type { Config } from 'tailwindcss';

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#ffffff',
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
      },
    },
  },
  plugins: [],
} satisfies Config;
