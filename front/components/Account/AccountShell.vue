<script setup lang="ts">
import { BRAND } from '~/constants/brand'
import PlannerHeader from '~/components/TripPlanner/PlannerHeader.vue'
const { title, subtitle } = defineProps<{ title: string; subtitle?: string }>()
const { locale, messages: m } = useAccountMessages()
const route = useRoute()
/** A trip detail page is not a child route of /trips, so the tab is matched by path prefix. */
const onTrips = computed(() => route.path.startsWith('/trips'))
useHead(() => ({ title: `${title} · ${BRAND.name}`, htmlAttrs: { lang: locale.value } }))
</script>

<template>
  <div>
    <PlannerHeader
      :locale="locale"
      :language-group-label="locale === 'mn' ? 'Хэл' : 'Language'"
      @set-locale="locale = $event"
    />
    <main class="mx-auto max-w-page px-4 pt-8 pb-20 sm:pt-12">
      <nav class="mb-8 flex gap-2 border-b border-line pb-4 text-sm" :aria-label="m.profile">
        <NuxtLink
          to="/trips"
          class="rounded-control px-4 py-2 text-ink-muted hover:bg-surface-muted"
          :class="{ '!bg-brand-soft !text-brand': onTrips }"
          :aria-current="onTrips ? 'page' : undefined"
        >
          {{ m.trips }}
        </NuxtLink>
        <NuxtLink
          to="/profile"
          class="rounded-control px-4 py-2 text-ink-muted hover:bg-surface-muted"
          active-class="!bg-brand-soft !text-brand"
        >
          {{ m.profile }}
        </NuxtLink>
      </nav>
      <div class="mb-8 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 class="font-display text-3xl font-bold">{{ title }}</h1>
          <p v-if="subtitle" class="mt-3 text-sm text-ink-muted">{{ subtitle }}</p>
        </div>
        <slot name="action" />
      </div>
      <slot />
    </main>
  </div>
</template>
