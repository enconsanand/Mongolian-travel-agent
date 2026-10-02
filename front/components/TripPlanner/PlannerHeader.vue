<script setup lang="ts">
import BrandMark from '~/components/Common/BrandMark.vue'
import ThemeToggle from '~/components/Common/ThemeToggle.vue'
import { BRAND } from '~/constants/brand'
import type { AppLocale } from '~/types/trip-planner'

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
    <div class="flex h-16 items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
      <div class="flex items-center gap-4">
        <NuxtLink to="/" class="flex items-center gap-2.5">
          <BrandMark class="h-9 w-9" />
          <span class="font-display text-xl font-bold text-ink">{{ BRAND.name }}</span>
        </NuxtLink>
      </div>
      <div class="flex items-center gap-2">
        <div
          class="flex rounded-control border border-line p-0.5 text-xs font-semibold"
          role="group"
          :aria-label="languageGroupLabel"
        >
          <button
            v-for="option in LOCALES"
            :key="option"
            type="button"
            class="rounded-[calc(var(--radius-control)-2px)] px-2.5 py-1.5 transition-colors"
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
