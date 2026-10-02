<script setup lang="ts">
import { onClickOutside } from '@vueuse/core'
import BrandMark from '~/components/Common/BrandMark.vue'
import ThemeToggle from '~/components/Common/ThemeToggle.vue'
import { BRAND } from '~/constants/brand'
import type { AppLocale } from '~/types/trip-planner'

const auth = useAuth()
const { userEmail } = useCookieAuth()
const { messages: account, contact } = useAccountMessages()
const menuOpen = ref(false)
const menu = ref<HTMLElement | null>(null)
onClickOutside(menu, () => {
  menuOpen.value = false
})
async function signOut() {
  menuOpen.value = false
  await auth.logout()
}
const route = useRoute()
watch(
  () => route.fullPath,
  () => {
    menuOpen.value = false
  }
)
const loginTarget = computed(() => ({
  path: '/login',
  query: !['/login', '/register'].includes(route.path) ? { redirect: route.fullPath } : {},
}))

const LOCALES: AppLocale[] = ['mn', 'en']
const THEME_LABELS: Record<AppLocale, { light: string; dark: string }> = {
  mn: { light: 'Цайвар горим', dark: 'Бараан горим' },
  en: { light: 'Light mode', dark: 'Dark mode' },
}

const { locale, languageGroupLabel } = defineProps<{
  locale: AppLocale
  languageGroupLabel: string
}>()

const emit = defineEmits<{
  'set-locale': [locale: AppLocale]
}>()

function localeButtonClass(option: AppLocale): string {
  return option === locale ? 'bg-brand text-brand-contrast' : 'text-ink-muted hover:text-ink'
}
</script>

<template>
  <header class="sticky top-0 z-30 border-b border-line bg-surface">
    <div class="flex h-16 items-center justify-between gap-2 px-4 sm:px-6 lg:px-8">
      <div class="flex items-center gap-4">
        <NuxtLink to="/" class="flex items-center gap-2.5">
          <BrandMark class="h-9 w-9" />
          <span class="font-display text-base font-bold sm:text-xl text-ink">{{ BRAND.name }}</span>
        </NuxtLink>
      </div>
      <div class="flex items-center gap-2">
        <template v-if="!auth.isLoggedIn.value && !['/login', '/register'].includes(route.path)">
          <NuxtLink :to="loginTarget" class="hidden px-2 text-sm font-semibold text-brand sm:inline-flex">
            {{ account.login }}
          </NuxtLink>
          <span class="mr-1 hidden md:inline-flex">
            <NuxtLink :to="{ path: '/register', query: loginTarget.query }" class="btn-primary px-3 py-2 text-sm">
              {{ account.register }}
            </NuxtLink>
          </span>
        </template>
        <NuxtLink
          v-if="auth.isLoggedIn.value"
          to="/trips"
          class="mr-2 hidden text-sm font-semibold text-ink-muted sm:inline-flex"
        >
          {{ account.trips }}
        </NuxtLink>
        <div ref="menu" class="relative" @keydown.esc="menuOpen = false">
          <button
            type="button"
            class="flex h-10 w-10 items-center justify-center rounded-control border border-line text-brand hover:bg-brand-soft"
            :aria-label="account.profile"
            :aria-expanded="menuOpen"
            aria-controls="account-menu"
            @click="menuOpen = !menuOpen"
          >
            <i class="pi pi-user" aria-hidden="true" />
          </button>
          <nav
            v-if="menuOpen"
            id="account-menu"
            :aria-label="account.profile"
            class="absolute right-0 z-40 mt-3 w-52 rounded-card border border-line bg-surface p-2 shadow-card"
          >
            <template v-if="auth.isLoggedIn.value">
              <p v-if="userEmail" class="mb-1 truncate border-b border-line px-4 pt-2 pb-3 text-xs text-ink-muted">
                {{ contact(userEmail) }}
              </p>
              <NuxtLink to="/profile" class="block rounded-control px-4 py-3 text-sm hover:bg-surface-muted">
                {{ account.profile }}
              </NuxtLink>
              <NuxtLink to="/trips" class="block rounded-control px-4 py-3 text-sm hover:bg-surface-muted">
                {{ account.trips }}
              </NuxtLink>
              <button
                type="button"
                class="w-full rounded-control px-4 py-3 text-left text-sm text-ink-muted hover:bg-surface-muted"
                @click="signOut"
              >
                {{ account.logout }}
              </button>
            </template>
            <template v-else>
              <NuxtLink :to="loginTarget" class="block rounded-control px-4 py-3 text-sm hover:bg-surface-muted">
                {{ account.login }}
              </NuxtLink>
              <NuxtLink
                :to="{ path: '/register', query: loginTarget.query }"
                class="block rounded-control px-4 py-3 text-sm hover:bg-surface-muted"
              >
                {{ account.register }}
              </NuxtLink>
            </template>
          </nav>
        </div>
        <div
          class="flex rounded-control border border-line p-0.5 text-xs font-semibold"
          role="group"
          :aria-label="languageGroupLabel"
        >
          <button
            v-for="option in LOCALES"
            :key="option"
            type="button"
            class="rounded-inner px-2.5 py-1.5 transition-colors"
            :class="localeButtonClass(option)"
            :aria-pressed="option === locale"
            @click="emit('set-locale', option)"
          >
            {{ option.toUpperCase() }}
          </button>
        </div>
        <ThemeToggle :light-label="THEME_LABELS[locale].light" :dark-label="THEME_LABELS[locale].dark" />
      </div>
    </div>
  </header>
</template>
