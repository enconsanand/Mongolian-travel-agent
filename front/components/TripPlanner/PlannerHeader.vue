<script setup lang="ts">
import type { AppLocale } from '~/types/trip-planner'

const LOCALES: AppLocale[] = ['mn', 'en']

const { locale, languageGroupLabel } = defineProps<{
  locale: AppLocale
  languageGroupLabel: string
}>()

const emit = defineEmits<{
  'set-locale': [locale: AppLocale]
}>()

function localeButtonClass(option: AppLocale): string {
  const isActive = option === locale
  return isActive ? 'rounded-full bg-emerald-500 px-3 py-1 text-slate-900' : 'rounded-full px-3 py-1 text-slate-300'
}
</script>

<template>
  <header class="glass-panel sticky top-0 z-30 border-x-0 border-t-0">
    <div class="mx-auto flex h-14 max-w-4xl items-center justify-between px-4">
      <div class="flex items-center gap-2">
        <i class="pi pi-compass text-xl text-emerald-400" aria-hidden="true" />
        <span class="text-sm font-semibold tracking-tight sm:text-base">Mongolian Travel AI Agent</span>
      </div>
      <div
        class="flex rounded-full bg-slate-800 p-0.5 text-xs font-medium"
        role="group"
        :aria-label="languageGroupLabel"
      >
        <button
          v-for="option in LOCALES"
          :key="option"
          type="button"
          :class="localeButtonClass(option)"
          :aria-pressed="option === locale"
          @click="emit('set-locale', option)"
        >
          {{ option.toUpperCase() }}
        </button>
      </div>
    </div>
  </header>
</template>
