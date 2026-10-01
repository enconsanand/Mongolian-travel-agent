<script setup lang="ts">
import type { AppLocale, TripPlannerMessages } from '~/types/trip-planner'
import { addDays, localIsoDate, MAX_TRIP_DAYS } from '~/utils/dates'
import { formatTripRange } from '~/utils/tripFacts'

const { ask, locale, messages, defaultStart, defaultEnd } = defineProps<{
  ask: 'place' | 'guests' | 'dates' | 'budget'
  locale: AppLocale
  messages: TripPlannerMessages
  /** Filled in already; the traveller can change either day */
  defaultStart: string
  defaultEnd: string
}>()

const emit = defineEmits<{ pick: [text: string] }>()

const choices = computed(() => messages.chat.choices)
const today = localIsoDate()
const startDate = ref(defaultStart)
const endDate = ref(defaultEnd)

const latestEnd = computed(() => (startDate.value ? addDays(startDate.value, MAX_TRIP_DAYS - 1) : ''))
const datesInvalid = computed(() =>
  Boolean(startDate.value && endDate.value && (endDate.value < startDate.value || endDate.value > latestEnd.value))
)

function guestLabel(count: number): string {
  if (locale === 'en' && count === 1) return '1 person'
  return `${count} ${choices.value.guestSuffix}`
}

function useDates() {
  if (!startDate.value || !endDate.value || datesInvalid.value) return
  emit('pick', formatTripRange(startDate.value, endDate.value, locale))
}
</script>

<template>
  <div class="flex flex-col gap-2">
    <div v-if="ask === 'place'" class="flex flex-wrap gap-2">
      <button
        v-for="place in choices.places"
        :key="place.value"
        type="button"
        class="prompt-chip"
        @click="emit('pick', place.value)"
      >
        {{ place.label }}
      </button>
    </div>

    <div v-else-if="ask === 'guests'" class="flex flex-wrap gap-2">
      <button
        v-for="count in choices.guests"
        :key="count"
        type="button"
        class="prompt-chip"
        @click="emit('pick', guestLabel(count))"
      >
        {{ guestLabel(count) }}
      </button>
    </div>

    <form v-else-if="ask === 'dates'" class="flex flex-col gap-2" @submit.prevent="useDates">
      <label class="flex items-center gap-2 text-xs text-ink-muted">
        <span class="w-14 shrink-0">{{ choices.fromDate }}</span>
        <input v-model="startDate" type="date" class="planner-date" :min="today" required />
      </label>
      <label class="flex items-center gap-2 text-xs text-ink-muted">
        <span class="w-14 shrink-0">{{ choices.toDate }}</span>
        <input
          v-model="endDate"
          type="date"
          class="planner-date"
          :min="startDate || today"
          :max="latestEnd || undefined"
          required
        />
      </label>
      <p v-if="datesInvalid" class="text-xs text-danger">{{ choices.datesInvalid }}</p>
      <button
        type="submit"
        class="btn-primary w-fit px-4 py-2 text-sm"
        :disabled="!startDate || !endDate || datesInvalid"
      >
        {{ choices.useDates }}
      </button>
    </form>

    <div v-else class="flex flex-wrap gap-2">
      <button
        v-for="budget in choices.budgets"
        :key="budget.value"
        type="button"
        class="prompt-chip"
        @click="emit('pick', budget.value)"
      >
        {{ budget.label }}
      </button>
    </div>
  </div>
</template>
