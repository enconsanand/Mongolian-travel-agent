<script setup lang="ts">
import type { PlanMessages } from '~/constants/tripPlan'
import type { Proposal } from '~/types/trip-plan'
import type { AppLocale } from '~/types/trip-planner'
import { formatMnt } from '~/utils/tripPlan'

const { proposal, locale, messages } = defineProps<{
  proposal: Proposal
  locale: AppLocale
  messages: PlanMessages
}>()

const MAX_DRIVE_DAY_MIN = 12 * 60

const placeName = (id: string | null) => (id ? proposal.catalog.places[id]?.name ?? id : '')

function nightsBetween(): number {
  const start = Date.parse(`${proposal.request.start_date}T00:00:00Z`)
  const end = Date.parse(`${proposal.request.end_date}T00:00:00Z`)
  if (!Number.isFinite(start) || !Number.isFinite(end) || end < start) return 0
  return Math.round((end - start) / 86_400_000)
}

/** Plans saved before the check still show a 23-hour driving day; treat that as not possible. */
const unfit = computed(() => {
  if (proposal.fit) return proposal.fit.feasible ? null : proposal.fit
  const first = proposal.days[0]
  if (!first) return null
  const longest = proposal.days.reduce((max, day) => (day.drive_time_min > max.drive_time_min ? day : max), first)
  if (longest.drive_time_min <= MAX_DRIVE_DAY_MIN) return null
  const driveDays = Math.ceil(longest.drive_time_min / MAX_DRIVE_DAY_MIN)
  return {
    feasible: false,
    min_nights: 2 * (driveDays - 1) + 1,
    drive_min: longest.drive_time_min,
    place_id: longest.to_place_id,
  }
})

const shownWarnings = computed(() => proposal.warnings.filter((warning) => warning !== 'no_availability'))

/** Ticket prices are not part of the stay booking, so they are summed here for display only. */
const separateEventsMnt = computed(() => {
  const guests = proposal.request.guests
  const seen = new Set<string>()
  let sum = 0
  for (const day of proposal.days) {
    for (const id of day.event_ids) {
      if (seen.has(id)) continue
      seen.add(id)
      sum += (proposal.catalog.events[id]?.ticket_price_mnt ?? 0) * guests
    }
  }
  return sum
})

const staysWithinBudget = computed(
  () => proposal.totals.budget_mnt === null || proposal.totals.stays_mnt <= proposal.totals.budget_mnt
)

const routeStops = computed(() => {
  const stops: { id: string; name: string; nights: number }[] = []
  for (const day of proposal.days.slice(0, -1)) {
    const last = stops.at(-1)
    if (last && day.from_place_id === day.to_place_id && day.to_place_id === last.id) last.nights += 1
    else stops.push({ id: day.to_place_id, name: placeName(day.to_place_id), nights: 1 })
  }
  return stops
})

const unfitText = computed(() => {
  const fit = unfit.value
  if (!fit) return ''
  return messages.notEnoughTime
    .replace('{place}', placeName(fit.place_id))
    .replace('{hours}', String(Math.max(1, Math.round(fit.drive_min / 60))))
    .replace('{nights}', String(nightsBetween()))
    .replace('{minNights}', String(fit.min_nights))
})
</script>

<template>
  <section class="panel p-5 sm:p-6">
    <p
      v-if="unfitText"
      class="rounded-control border border-danger bg-danger-soft p-3 text-sm leading-relaxed text-danger"
      role="alert"
    >
      {{ unfitText }}
    </p>
    <p v-else class="text-sm leading-relaxed sm:text-base">{{ proposal.summary }}</p>

    <ol v-if="routeStops.length" class="mt-4 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm">
      <li v-for="(stop, index) in routeStops" :key="`${stop.id}-${index}`" class="flex items-center gap-2">
        <span v-if="index" class="text-brand" aria-hidden="true">→</span>
        <span class="rounded-full border border-line bg-brand-soft px-3 py-1">
          {{ stop.name }}
          <span class="text-ink-muted">· {{ stop.nights }}</span>
        </span>
      </li>
    </ol>

    <div v-if="proposal.places.length" class="mt-5">
      <h2 class="font-sans text-xs font-semibold tracking-wide text-ink-muted uppercase">{{ messages.places }}</h2>
      <ul class="mt-2 space-y-1.5 text-sm">
        <li v-for="place in proposal.places" :key="place.query" class="flex items-start gap-2">
          <i
            :class="
              place.status === 'included'
                ? 'pi pi-check-circle text-success'
                : 'pi pi-exclamation-triangle text-warning'
            "
            class="mt-0.5"
            aria-hidden="true"
          />
          <span>
            <span class="font-medium">{{ place.query }}</span>
            <span v-if="place.status === 'included'" class="text-ink-muted">
              → {{ placeName(place.place_id) }} · {{ messages.placeIncluded }}
            </span>
            <span v-else class="text-warning">· {{ messages.placeUnresolved }}</span>
          </span>
        </li>
      </ul>
    </div>

    <ul v-if="shownWarnings.length" class="mt-4 space-y-1.5 text-sm text-warning" role="status">
      <li v-for="warning in shownWarnings" :key="warning">
        <i class="pi pi-info-circle mr-1" aria-hidden="true" />
        {{ messages.warnings[warning] }}
      </li>
    </ul>

    <dl class="mt-5 grid grid-cols-2 gap-x-4 gap-y-1 border-t border-line pt-4 text-sm">
      <dt class="text-ink-muted">{{ messages.staysTotal }}</dt>
      <dd class="text-right">{{ formatMnt(proposal.totals.stays_mnt, locale) }}</dd>
      <template v-if="separateEventsMnt">
        <dt class="text-ink-muted">{{ messages.eventsTotal }}</dt>
        <dd class="text-right">{{ formatMnt(separateEventsMnt, locale) }}</dd>
      </template>
      <dt class="font-semibold">{{ messages.total }}</dt>
      <dd class="text-right text-lg font-semibold text-brand">
        {{ formatMnt(proposal.totals.stays_mnt, locale) }}
      </dd>
      <dt class="text-ink-muted">{{ messages.budget }}</dt>
      <dd class="text-right" :class="staysWithinBudget ? 'text-ink-muted' : 'text-danger'">
        {{ proposal.totals.budget_mnt === null ? messages.noLimit : formatMnt(proposal.totals.budget_mnt, locale) }}
      </dd>
    </dl>
  </section>
</template>
