<script setup lang="ts">
import type { PlanMessages } from '~/constants/tripPlan'
import type { TransportOption, TransportPlan } from '~/types/trip-plan'
import type { AppLocale } from '~/types/trip-planner'
import { formatMnt } from '~/utils/tripPlan'

/** The way of travel the planner picked for the whole trip, why, and what the other ways would cost */
const { plan, guests, locale, messages } = defineProps<{
  plan: TransportPlan
  guests: number
  locale: AppLocale
  messages: PlanMessages
}>()

const ICONS = {
  public: 'pi pi-ticket',
  with_driver: 'pi pi-user',
  self_drive: 'pi pi-car',
  own_car: 'pi pi-home',
} as const

function title(option: TransportOption) {
  const kind = messages.transportKinds[option.kind]
  if (!option.vehicle) return kind
  return `${kind} · ${option.vehicle}${option.vehicles > 1 ? ` × ${option.vehicles}` : ''}`
}

function parts(option: TransportOption) {
  const words = messages.transportParts
  return [
    option.rent_mnt ? `${words.rent} ${formatMnt(option.rent_mnt, locale)}` : '',
    option.fuel_mnt ? `${words.fuel} ${formatMnt(option.fuel_mnt, locale)}` : '',
    option.tickets_mnt ? `${words.tickets} ${formatMnt(option.tickets_mnt, locale)}` : '',
  ]
    .filter(Boolean)
    .join(' + ')
}

const reason = computed(() =>
  messages.transportReasons[plan.reason].replace('{guests}', String(guests)).replace('{days}', String(plan.chosen.days))
)
</script>

<template>
  <div class="mt-4 rounded-control border border-line p-3 text-sm">
    <p class="text-xs font-semibold tracking-wide text-ink-muted uppercase">{{ messages.transportPicked }}</p>
    <p class="mt-1.5 flex items-start gap-2 font-medium">
      <i :class="ICONS[plan.chosen.kind]" class="mt-0.5 text-brand" aria-hidden="true" />
      <span class="flex-1">{{ title(plan.chosen) }}</span>
      <span class="shrink-0">{{ formatMnt(plan.chosen.total_mnt, locale) }}</span>
    </p>
    <p class="mt-0.5 pl-6 text-xs text-ink-muted">{{ parts(plan.chosen) }}</p>
    <p class="mt-2 pl-6 text-xs text-ink-muted">
      <i class="pi pi-sparkles mr-1 text-brand" aria-hidden="true" />
      {{ reason }}
    </p>

    <template v-if="plan.alternatives.length">
      <p class="mt-3 text-xs font-semibold tracking-wide text-ink-muted uppercase">{{ messages.transportOthers }}</p>
      <ul class="mt-1.5 space-y-1">
        <li v-for="option in plan.alternatives" :key="option.kind" class="flex items-start gap-2 text-xs">
          <i :class="ICONS[option.kind]" class="mt-0.5 text-ink-subtle" aria-hidden="true" />
          <span class="flex-1 text-ink-muted">{{ title(option) }}</span>
          <span class="shrink-0 text-ink-muted">{{ formatMnt(option.total_mnt, locale) }}</span>
        </li>
      </ul>
    </template>
  </div>
</template>
