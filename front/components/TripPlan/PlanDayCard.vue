<script setup lang="ts">
import { STAY_TYPE_LABELS, type PlanMessages } from '~/constants/tripPlan'
import { UNIT_LABELS } from '~/constants/checkout'
import type { PlanDay, Proposal } from '~/types/trip-plan'
import type { AppLocale } from '~/types/trip-planner'
import { formatDriveTime, formatMnt } from '~/utils/tripPlan'

const { day, catalog, locale, messages } = defineProps<{
  day: PlanDay
  catalog: Proposal['catalog']
  locale: AppLocale
  messages: PlanMessages
  /** The day has a night (every day but the last) */
  hasNight: boolean
}>()

const placeName = (id: string) => catalog.places[id]?.name ?? id
const isFreeDay = computed(() => day.from_place_id === day.to_place_id && day.via_place_ids.length === 0)
const stay = computed(() => (day.stay ? catalog.stays[day.stay.stay_id] : undefined))
const credit = computed(() => stay.value?.images[0])
const dateLabel = computed(() =>
  new Date(`${day.date}T00:00:00`).toLocaleDateString(locale === 'mn' ? 'mn-MN' : 'en-US', {
    month: 'short',
    day: 'numeric',
    weekday: 'short',
  })
)
</script>

<template>
  <li class="glass-panel rounded-2xl p-4 sm:p-5">
    <div class="flex items-baseline justify-between gap-3">
      <p class="text-xs font-semibold tracking-wide text-emerald-300 uppercase">
        {{ locale === 'mn' ? `${day.day}-р ${messages.day}` : `${messages.day} ${day.day}` }} · {{ dateLabel }}
      </p>
      <p v-if="day.distance_km" class="shrink-0 text-xs text-slate-400">
        <i class="pi pi-car mr-1" aria-hidden="true" />
        {{ day.distance_km }} {{ locale === 'mn' ? 'км' : 'km' }} ·
        {{ formatDriveTime(day.drive_time_min, locale) }}
      </p>
    </div>

    <h3 class="mt-1 text-base font-semibold sm:text-lg">
      <template v-if="isFreeDay">{{ messages.freeDay }} · {{ placeName(day.to_place_id) }}</template>
      <template v-else>{{ placeName(day.from_place_id) }} → {{ placeName(day.to_place_id) }}</template>
    </h3>
    <p v-if="day.via_place_ids.length" class="mt-1 text-sm text-cyan-200">
      <i class="pi pi-map-marker mr-1" aria-hidden="true" />
      {{ messages.via }}:
      {{ day.via_place_ids.map(placeName).join(', ') }}
    </p>
    <p v-if="day.note" class="mt-2 text-sm leading-relaxed text-slate-300">{{ day.note }}</p>

    <div v-if="day.stay && stay" class="mt-4 flex gap-3 rounded-xl bg-slate-900/60 p-3">
      <figure class="w-28 shrink-0 sm:w-36">
        <img
          :src="stay.cover_image_url"
          :alt="stay.name"
          class="aspect-4/3 w-full rounded-lg object-cover"
          loading="lazy"
        />
        <figcaption v-if="credit" class="mt-1 truncate text-[10px] text-slate-500">
          <a :href="credit.source" target="_blank" rel="noopener" class="hover:underline">
            {{ messages.photo }}: {{ credit.author }}, {{ credit.license }}
          </a>
        </figcaption>
      </figure>
      <div class="min-w-0 text-sm">
        <p class="text-xs text-slate-400">{{ messages.stay }} · {{ STAY_TYPE_LABELS[stay.type]?.[locale] }}</p>
        <p class="font-semibold">{{ stay.name }}</p>
        <p class="text-xs text-amber-300">
          <i class="pi pi-star-fill mr-1" aria-hidden="true" />
          {{ stay.rating }} ({{ stay.reviews_count }})
        </p>
        <p class="mt-1 text-xs text-slate-300">
          {{ day.stay.units }} {{ messages.units }}
          {{ UNIT_LABELS[day.stay.unit_type]?.[locale] ?? day.stay.unit_type }} · {{ day.stay.nights }}
          {{ messages.nights }}
        </p>
        <p class="mt-1 font-semibold text-emerald-300">{{ formatMnt(day.stay.total_mnt, locale) }}</p>
      </div>
    </div>
    <p v-else-if="hasNight && !day.stay_id" class="mt-3 text-sm text-amber-300">
      <i class="pi pi-exclamation-circle mr-1" aria-hidden="true" />
      {{ messages.noStay }}
    </p>

    <div v-if="day.event_ids.length" class="mt-3">
      <p class="text-xs text-slate-400">{{ messages.events }}</p>
      <ul class="mt-1 flex flex-wrap gap-2">
        <li
          v-for="eventId in day.event_ids"
          :key="eventId"
          class="rounded-full border border-cyan-400/40 bg-cyan-400/10 px-3 py-1 text-xs text-cyan-100"
        >
          <i class="pi pi-flag mr-1" aria-hidden="true" />
          {{ catalog.events[eventId]?.name }} ·
          {{
            catalog.events[eventId]?.ticket_price_mnt
              ? formatMnt(catalog.events[eventId]!.ticket_price_mnt, locale)
              : messages.free
          }}
        </li>
      </ul>
    </div>
  </li>
</template>
