import { definePreset } from '@primeuix/themes'
import Aura from '@primeuix/themes/aura'

const AppPreset = definePreset(Aura, {
  primitive: {
    borderRadius: {
      none: '0',
      xs: '2px',
      sm: '4px',
      md: '6px',
      lg: '8px',
      xl: '12px',
    },

    // UI Base Colors
    slate: {
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

    // Primary Blue
    blue: {
      50: '#eff6ff',
      100: '#dbeafe',
      200: '#bfdbfe',
      300: '#93c5fd',
      400: '#60a5fa',
      500: '#3b82f6',
      600: '#2563eb',
      700: '#1d4ed8',
      800: '#1e40af',
      900: '#1e3a8a',
      950: '#172554',
    },
  },

  semantic: {
    transitionDuration: '0.2s',
    focusRing: {
      width: '2px',
      style: 'solid',
      color: '{primary.500}',
      offset: '1px',
      shadow: '0 0 0 2px rgba(59, 130, 246, 0.3)',
    },
    disabledOpacity: '0.5',
    iconSize: '1.125rem',
    anchorGutter: '4px',

    primary: {
      50: '#eff6ff',
      100: '#dbeafe',
      200: '#bfdbfe',
      300: '#93c5fd',
      400: '#60a5fa',
      500: '#3b82f6',
      600: '#2563eb',
      700: '#1d4ed8',
      800: '#1e40af',
      900: '#1e3a8a',
      950: '#172554',
    },

    formField: {
      paddingX: '1rem',
      paddingY: '0.75rem',
      sm: {
        fontSize: '0.875rem',
        paddingX: '0.75rem',
        paddingY: '0.5rem',
      },
      lg: {
        fontSize: '1.125rem',
        paddingX: '1.25rem',
        paddingY: '1rem',
      },
      borderRadius: '{border.radius.md}',
      focusRing: {
        width: '2px',
        style: 'solid',
        color: '{primary.500}',
        offset: '0',
        shadow: '0 0 0 2px rgba(59, 130, 246, 0.2)',
      },
      transitionDuration: '{transition.duration}',
    },

    colorScheme: {
      light: {
        surface: {
          0: '#ffffff',
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
        primary: {
          color: '{primary.600}',
          contrastColor: '#ffffff',
          hoverColor: '{primary.700}',
          activeColor: '{primary.800}',
        },
        highlight: {
          background: '{primary.50}',
          focusBackground: '{primary.100}',
          color: '{primary.800}',
          focusColor: '{primary.900}',
        },
      },
    },
  },
})

export default {
  preset: AppPreset,
  options: {
    darkModeSelector: '.fake-dark-selector',
    ripple: false,
  },
}
