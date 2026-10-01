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

const placeName = (id: string | null) => (id ? (proposal.catalog.places[id]?.name ?? id) : '')
</script>

<template>
  <section class="panel p-5 sm:p-6">
    <p class="text-sm leading-relaxed sm:text-base">{{ proposal.summary }}</p>

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

    <ul v-if="proposal.warnings.length" class="mt-4 space-y-1.5 text-sm text-warning" role="status">
      <li v-for="warning in proposal.warnings" :key="warning">
        <i class="pi pi-info-circle mr-1" aria-hidden="true" />
        {{ messages.warnings[warning] }}
      </li>
    </ul>

    <dl class="mt-5 grid grid-cols-2 gap-x-4 gap-y-1 border-t border-line pt-4 text-sm">
      <dt class="text-ink-muted">{{ messages.staysTotal }}</dt>
      <dd class="text-right">{{ formatMnt(proposal.totals.stays_mnt, locale) }}</dd>
      <template v-if="proposal.totals.events_mnt">
        <dt class="text-ink-muted">{{ messages.eventsTotal }}</dt>
        <dd class="text-right">{{ formatMnt(proposal.totals.events_mnt, locale) }}</dd>
      </template>
      <dt class="font-semibold">{{ messages.total }}</dt>
      <dd class="text-right text-lg font-semibold text-brand">
        {{ formatMnt(proposal.totals.total_mnt, locale) }}
      </dd>
      <dt class="text-ink-muted">{{ messages.budget }}</dt>
      <dd class="text-right" :class="proposal.totals.within_budget ? 'text-ink-muted' : 'text-danger'">
        {{ proposal.totals.budget_mnt === null ? messages.noLimit : formatMnt(proposal.totals.budget_mnt, locale) }}
      </dd>
    </dl>
  </section>
</template>
