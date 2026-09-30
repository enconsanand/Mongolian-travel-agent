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
  <section class="glass-panel rounded-2xl p-5 sm:p-6">
    <p class="text-sm leading-relaxed text-slate-200 sm:text-base">{{ proposal.summary }}</p>

    <div v-if="proposal.places.length" class="mt-5">
      <h2 class="text-xs font-semibold tracking-wide text-slate-400 uppercase">{{ messages.places }}</h2>
      <ul class="mt-2 space-y-1.5 text-sm">
        <li v-for="place in proposal.places" :key="place.query" class="flex items-start gap-2">
          <i
            :class="
              place.status === 'included'
                ? 'pi pi-check-circle text-emerald-300'
                : 'pi pi-exclamation-triangle text-amber-300'
            "
            class="mt-0.5"
            aria-hidden="true"
          />
          <span>
            <span class="font-medium">{{ place.query }}</span>
            <span v-if="place.status === 'included'" class="text-slate-400">
              → {{ placeName(place.place_id) }} · {{ messages.placeIncluded }}
            </span>
            <span v-else class="text-amber-300">· {{ messages.placeUnresolved }}</span>
          </span>
        </li>
      </ul>
    </div>

    <ul v-if="proposal.warnings.length" class="mt-4 space-y-1.5 text-sm text-amber-300" role="status">
      <li v-for="warning in proposal.warnings" :key="warning">
        <i class="pi pi-info-circle mr-1" aria-hidden="true" />
        {{ messages.warnings[warning] }}
      </li>
    </ul>

    <dl class="mt-5 grid grid-cols-2 gap-x-4 gap-y-1 border-t border-slate-800 pt-4 text-sm">
      <dt class="text-slate-400">{{ messages.staysTotal }}</dt>
      <dd class="text-right">{{ formatMnt(proposal.totals.stays_mnt, locale) }}</dd>
      <template v-if="proposal.totals.events_mnt">
        <dt class="text-slate-400">{{ messages.eventsTotal }}</dt>
        <dd class="text-right">{{ formatMnt(proposal.totals.events_mnt, locale) }}</dd>
      </template>
      <dt class="font-semibold">{{ messages.total }}</dt>
      <dd class="text-right text-lg font-semibold text-emerald-300">
        {{ formatMnt(proposal.totals.total_mnt, locale) }}
      </dd>
      <dt class="text-slate-400">{{ messages.budget }}</dt>
      <dd class="text-right" :class="proposal.totals.within_budget ? 'text-slate-300' : 'text-rose-300'">
        {{ proposal.totals.budget_mnt === null ? messages.noLimit : formatMnt(proposal.totals.budget_mnt, locale) }}
      </dd>
    </dl>
  </section>
</template>
