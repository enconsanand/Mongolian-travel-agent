<script setup lang="ts">
import { PLAN_MESSAGES } from '~/constants/tripPlan'
import type { Proposal } from '~/types/trip-plan'
import type { AppLocale, TripPlannerMessages } from '~/types/trip-planner'
import { formatMnt } from '~/utils/tripPlan'

/** The agent's answer in the chat: the itinerary at a glance, with a link to its full page for booking */
const {
  proposal,
  locale,
  labels,
  compact = false,
} = defineProps<{
  proposal: Proposal
  locale: AppLocale
  labels: TripPlannerMessages['chat']
  /** Leave out the cover photo, for a small chat box */
  compact?: boolean
}>()

const planLabels = computed(() => PLAN_MESSAGES[locale])
const placeName = (id: string) => proposal.catalog.places[id]?.name ?? id

const days = computed(() =>
  proposal.days.map((day) => ({
    day: day.day,
    route:
      day.from_place_id === day.to_place_id
        ? placeName(day.to_place_id)
        : `${placeName(day.from_place_id)} → ${placeName(day.to_place_id)}`,
    stay: day.stay_id ? proposal.catalog.stays[day.stay_id]?.name : undefined,
  }))
)
const cover = computed(() => {
  const firstStay = proposal.days.find((day) => day.stay_id)?.stay_id
  return firstStay ? proposal.catalog.stays[firstStay]?.cover_image_url : undefined
})
</script>

<template>
  <article class="panel w-full overflow-hidden">
    <img v-if="cover && !compact" :src="cover" alt="" class="h-36 w-full object-cover" loading="lazy" />
    <div class="p-5">
      <div class="flex items-baseline justify-between gap-3">
        <h3 class="font-display text-lg font-semibold">{{ proposal.days.length }} {{ labels.days }}</h3>
        <span class="text-xs text-ink-subtle">{{ planLabels.version }} {{ proposal.version }}</span>
      </div>
      <p class="mt-1 text-sm leading-relaxed text-ink-muted">{{ proposal.summary }}</p>

      <ol class="mt-4 space-y-2.5 border-l-2 border-line pl-4">
        <li v-for="item in days" :key="item.day" class="relative text-sm">
          <span class="absolute top-1.5 -left-[1.4rem] h-2.5 w-2.5 rounded-full bg-brand" aria-hidden="true" />
          <span class="font-semibold">{{ item.day }}.</span>
          {{ item.route }}
          <span v-if="item.stay" class="block text-xs text-ink-muted">
            <i class="pi pi-home mr-1 text-[0.7rem]" aria-hidden="true" />
            {{ item.stay }}
          </span>
        </li>
      </ol>

      <ul v-if="proposal.warnings.length" class="mt-4 space-y-1 text-xs text-warning">
        <li v-for="warning in proposal.warnings" :key="warning">
          <i class="pi pi-info-circle mr-1" aria-hidden="true" />
          {{ planLabels.warnings[warning] }}
        </li>
      </ul>

      <div class="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-line pt-4">
        <p class="text-sm">
          <span class="text-ink-muted">{{ labels.total }}:</span>
          <span class="ml-1 text-base font-semibold text-brand">
            {{ formatMnt(proposal.totals.total_mnt, locale) }}
          </span>
        </p>
        <NuxtLink :to="`/plan/${proposal.id}`" class="btn-primary px-4 py-2 text-sm">
          {{ labels.openPlan }}
          <i class="pi pi-arrow-right text-xs" aria-hidden="true" />
        </NuxtLink>
      </div>
    </div>
  </article>
</template>
