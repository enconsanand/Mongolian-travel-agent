<script setup lang="ts">
import type { PlanMessages } from '~/constants/tripPlan'
import type { EventView } from '~/types/trip-plan'
import type { AppLocale } from '~/types/trip-planner'
import { formatMnt, formatMonthDay } from '~/utils/tripPlan'

const { events, locale, messages } = defineProps<{
  events: (EventView & { id: string })[]
  locale: AppLocale
  messages: PlanMessages
}>()
</script>

<template>
  <section v-if="events.length" class="panel p-5 sm:p-6">
    <h2 class="font-sans text-xs font-semibold tracking-wide text-ink-muted uppercase">{{ messages.events }}</h2>
    <ul class="mt-3 space-y-3">
      <li v-for="event in events" :key="event.id" class="rounded-control border border-accent/40 bg-surface-muted p-3">
        <div class="flex gap-3">
          <img
            v-if="event.cover_image_url"
            :src="event.cover_image_url"
            :alt="event.name"
            class="h-16 w-24 shrink-0 rounded-inner object-cover"
            loading="lazy"
          />
          <div class="min-w-0 text-sm">
            <p class="font-semibold">{{ event.name }}</p>
            <p class="mt-1 text-xs text-accent-ink">
              {{ formatMonthDay(event.start_date, locale) }} – {{ formatMonthDay(event.end_date, locale) }}
            </p>
            <p v-if="event.description" class="mt-1 text-xs leading-relaxed text-ink-muted">{{ event.description }}</p>
            <p class="mt-2 text-xs text-ink-muted">
              {{ event.ticket_price_mnt ? formatMnt(event.ticket_price_mnt, locale) : messages.free }}
              · {{ messages.eventApart }}
            </p>
            <p class="mt-2 flex flex-wrap gap-2">
              <a
                v-if="event.phone"
                :href="`tel:${event.phone.replace(/\s/g, '')}`"
                class="rounded-full border border-line px-3 py-1 text-xs hover:border-brand"
              >
                {{ messages.eventPhone }}: {{ event.phone }}
              </a>
              <a
                v-if="event.url"
                :href="event.url"
                target="_blank"
                rel="noopener"
                class="rounded-full border border-line px-3 py-1 text-xs hover:border-brand"
              >
                {{ messages.eventSite }}
              </a>
            </p>
          </div>
        </div>
      </li>
    </ul>
  </section>
</template>
