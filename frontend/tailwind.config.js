/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{svelte,js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          950: '#041f15',
          900: '#0a2e1f',
          800: '#0f3d2a',
          700: '#145c3e',
          600: '#10b981',
          500: '#34d399',
          400: '#6ee7b7',
          300: '#a7f3d0',
          200: '#d1fae5',
          100: '#ecfdf5',
          50:  '#f0fdf4',
        },
        surface: {
          0: '#ffffff',
          50: '#f8fafb',
          100: '#f1f5f9',
          200: '#e2e8f0',
          300: '#cbd5e1',
        },
        txt: {
          primary: '#1f2937',
          secondary: '#4b5563',
          muted: '#6b7280',
          faint: '#9ca3af',
        },
        speaker: {
          0: '#10b981',
          1: '#3b82f6',
          2: '#f59e0b',
          3: '#8b5cf6',
          4: '#ef4444',
          5: '#06b6d4',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
