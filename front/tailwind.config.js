/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './components/**/*.{js,vue,ts}',
    './layouts/**/*.vue',
    './pages/**/*.vue',
    './plugins/**/*.{js,ts}',
    './nuxt.config.{js,ts}',
    './app.vue',
    './node_modules/primevue/**/*.{vue,js,ts,jsx,tsx}',
    './node_modules/@primeuix/**/*.{vue,js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['PT Sans Caption', 'sans-serif'],
        mono: ['Roboto Mono', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
      colors: {
        thermal: {
          'hot-water': {
            50: '#fef7f0',
            100: '#feecdc',
            200: '#fcd9bd',
            300: '#fdba8c',
            400: '#ff8a4c',
            500: '#ff5722',
            600: '#ea580c',
            700: '#c2410c',
            800: '#9a3412',
            900: '#7c2d12',
            950: '#431407',
          },
          'cold-water': {
            50: '#eff6ff',
            100: '#dbeafe',
            200: '#bfdbfe',
            300: '#93c5fd',
            400: '#60a5fa',
            500: '#2563eb',
            600: '#1d4ed8',
            700: '#1e40af',
            800: '#1e3a8a',
            900: '#1e3a8a',
            950: '#172554',
          },
          steam: {
            50: '#f8fafc',
            100: '#f1f5f9',
            200: '#e2e8f0',
            300: '#cbd5e1',
            400: '#94a3b8',
            500: '#64748b',
            600: '#475569',
            700: '#334155',
            800: '#1e293b',
            900: '#0f172a',
            950: '#020617',
          },
          'high-temp': {
            50: '#fef2f2',
            100: '#fee2e2',
            200: '#fecaca',
            300: '#fca5a5',
            400: '#f87171',
            500: '#dc2626',
            600: '#b91c1c',
            700: '#991b1b',
            800: '#7f1d1d',
            900: '#7f1d1d',
            950: '#450a0a',
          },
        },
        importance: {
          high: '#dc2626',
          medium: '#f59e0b',
          low: '#10b981',
          minimal: '#6b7280',
        },
        confidence: {
          excellent: '#059669',
          good: '#10b981',
          fair: '#f59e0b',
          poor: '#ef4444',
          critical: '#dc2626',
        },
        status: {
          active: '#059669',
          training: '#f59e0b',
          error: '#dc2626',
          inactive: '#6b7280',
        },
        alert: {
          overheating: '#dc2626',
          underperforming: '#f59e0b',
          optimal: '#059669',
          warning: '#ea580c',
          critical: '#991b1b',
        },
      },
      boxShadow: {
        'xai-highlight': '0 0 0 2px rgba(59, 130, 246, 0.3)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in': 'fadeIn 0.5s ease-in-out',
        'slide-up': 'slideUp 0.3s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
      },
    },
  },
  safelist: [
    {
      pattern: /^p-/,
      variants: ['hover', 'focus', 'active', 'disabled'],
    },
    {
      pattern:
        /^(bg|text|border)-thermal-(hot-water|cold-water|steam|high-temp)-(50|100|200|300|400|500|600|700|800|900|950)$/,
      variants: ['hover', 'focus'],
    },
    {
      pattern:
        /^(bg|text|border)-(importance|confidence|status|alert)-(high|medium|low|minimal|excellent|good|fair|poor|critical|active|training|error|inactive|overheating|underperforming|optimal|warning)$/,
      variants: ['hover', 'focus'],
    },
    {
      pattern:
        /^(bg|text|border)-(blue|green|red|amber|purple|orange|slate)-(50|100|200|300|400|500|600|700|800|900|950)$/,
      variants: ['hover', 'focus'],
    },
  ],
  plugins: [],
}
