// https://v3.nuxtjs.org/api/configuration/nuxt.config
// @ts-nocheck
import tailwindcss from '@tailwindcss/vite'
import ThemeConfig from './assets/themes/config.js'

export default defineNuxtConfig({
  devtools: { enabled: process.env.NODE_ENV !== 'production' },
  app: {
    pageTransition: { name: 'page', mode: 'out-in' },
    head: {
      title: 'App',
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
          content: 'light',
        },
      ],
      link: [
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
          href: 'https://fonts.googleapis.com/css2?family=Mulish:wght@400;700&display=swap',
        },
      ],
    },
  },
  components: true,
  runtimeConfig: {
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || 'http://localhost:8000/api/v1',
    },
  },
  modules: ['@pinia/nuxt', '@nuxt/image', '@nuxtjs/robots', '@primevue/nuxt-module', '@nuxt/eslint'],
  primevue: {
    options: {
      theme: {
        preset: ThemeConfig.preset,
        options: {
          ...ThemeConfig.options,
        },
      },
    },
  },
  image: {
    format: ['webp'],
    provider: 'ipx',
  },
  pinia: {
    storesDirs: ['./stores/**'],
    autoImports: ['defineStore', ['defineStore', 'definePiniaStore']],
  },
  robots: {
    UserAgent: '*',
    Disallow: ['/api/', '/.nuxt/', '/admin/'],
    Allow: '/',
  },
  css: ['~/assets/css/main.css'],
  features: {
    inlineStyles: true,
  },
  build: {
    transpile: ['primevue', '@primeuix/themes'],
  },
  vite: {
    plugins: [tailwindcss()],
    define: {
      'process.env.DEBUG': false,
    },
    optimizeDeps: {
      include: ['@tanstack/vue-query', 'zod', 'vue3-toastify'],
    },
    ssr: {
      noExternal: ['primevue', '@primeuix/themes'],
      external: ['vue3-toastify'],
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

            return [
              "default-src 'self'",
              "script-src 'self' " + (process.env.NODE_ENV === 'development' ? "'unsafe-inline' 'unsafe-eval'" : ''),
              "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net",
              "font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net",
              "img-src 'self' data: https:",
              "connect-src 'self' " + apiOrigin + ' ws: wss:',
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
