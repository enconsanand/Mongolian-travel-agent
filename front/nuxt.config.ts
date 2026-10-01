// https://v3.nuxtjs.org/api/configuration/nuxt.config
import tailwindcss from '@tailwindcss/vite'

export default defineNuxtConfig({
  devtools: { enabled: process.env.NODE_ENV !== 'production' },
  app: {
    pageTransition: { name: 'page', mode: 'out-in' },
    head: {
      title: 'NomadRoute',
      htmlAttrs: {
        lang: 'en',
      },
      meta: [
        { charset: 'utf-8' },
        {
          name: 'viewport',
          content: 'width=device-width, initial-scale=1',
        },
        {
          name: 'color-scheme',
          content: 'light dark',
        },
      ],
      link: [
        { rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg' },
        { rel: 'icon', type: 'image/x-icon', href: '/favicon/favicon.ico' },
        {
          rel: 'apple-touch-icon',
          sizes: '180x180',
          href: '/favicon/apple-touch-icon.png',
        },
        {
          rel: 'icon',
          type: 'image/png',
          sizes: '32x32',
          href: '/favicon/favicon-32x32.png',
        },
        {
          rel: 'icon',
          type: 'image/png',
          sizes: '16x16',
          href: '/favicon/favicon-16x16.png',
        },
        {
          rel: 'icon',
          type: 'image/png',
          sizes: '192x192',
          href: '/favicon/android-chrome-192x192.png',
        },
        { rel: 'manifest', href: '/favicon/site.webmanifest' },
        {
          rel: 'preconnect',
          href: 'https://fonts.googleapis.com',
          crossorigin: 'anonymous',
        },
        {
          rel: 'preconnect',
          href: 'https://fonts.gstatic.com',
          crossorigin: 'anonymous',
        },
        {
          rel: 'stylesheet',
          href: 'https://fonts.googleapis.com/css2?family=Noto+Sans:wght@400;500;600;700&family=Noto+Serif:wght@600;700&display=swap',
        },
      ],
    },
  },
  components: true,
  runtimeConfig: {
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || 'http://localhost:8000/api/v1',
      // Demo only: base URL of the QPay simulator, for the "Pay with Sim Bank" button. Leave empty for real QPay.
      qpaySimBase: process.env.NUXT_PUBLIC_QPAY_SIM_BASE || '',
    },
  },
  modules: ['@nuxtjs/robots', '@nuxt/eslint'],
  css: ['~/assets/css/main.css', '~/assets/css/trip-planner.css'],
  features: {
    inlineStyles: true,
  },
  vite: {
    plugins: [tailwindcss()],
    define: {
      'process.env.DEBUG': false,
    },
  },
  eslint: {
    config: {
      standalone: true,
    },
  },
  imports: {
    dirs: ['types', 'composables/**'],
  },
  nitro: {
    routeRules: {
      '/**': {
        headers: {
          'Content-Security-Policy': (() => {
            const apiBase = process.env.NUXT_PUBLIC_API_BASE || 'http://localhost:8000/api/v1'
            const apiOrigin = new URL(apiBase).origin
            const simBase = process.env.NUXT_PUBLIC_QPAY_SIM_BASE
            const simOrigin = simBase ? ' ' + new URL(simBase).origin : ''

            return [
              "default-src 'self'",
              "script-src 'self' " + (process.env.NODE_ENV === 'development' ? "'unsafe-inline' 'unsafe-eval'" : ''),
              "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net",
              "font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net",
              "img-src 'self' data: https:",
              "connect-src 'self' " + apiOrigin + simOrigin + ' ws: wss:',
              "frame-ancestors 'none'",
              "base-uri 'self'",
              "form-action 'self'",
            ].join('; ')
          })(),
          'X-Frame-Options': 'DENY',
          'X-Content-Type-Options': 'nosniff',
          'Referrer-Policy': 'strict-origin-when-cross-origin',
          'Permissions-Policy': 'camera=(), microphone=(), geolocation=()',
          'X-XSS-Protection': '1; mode=block',
          // Omitted in dev so HTTP-only local setups are not locked out
          ...(process.env.NODE_ENV === 'production'
            ? { 'Strict-Transport-Security': 'max-age=31536000; includeSubDomains; preload' }
            : {}),
        },
      },
    },
  },
})
