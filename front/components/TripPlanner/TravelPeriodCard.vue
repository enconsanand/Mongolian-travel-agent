<script setup lang="ts">
import PreferenceCardFrame from '~/components/TripPlanner/PreferenceCardFrame.vue'
import type { PeriodPreferenceCard } from '~/types/trip-planner'
import { addDays, localIsoDate, MAX_TRIP_DAYS, travelPeriodError } from '~/utils/dates'

const { card, requiredLabel, startLabel, endLabel, invalidLabel, tooLongLabel } = defineProps<{
  card: PeriodPreferenceCard
  requiredLabel: string
  startLabel: string
  endLabel: string
  invalidLabel: string
  tooLongLabel: string
}>()

const emit = defineEmits<{
  'set-start': [value: string]
  'set-end': [value: string]
}>()

const today = localIsoDate()
const rangeError = computed(() => {
  const error = travelPeriodError(card.period)
  return error === 'outOfOrder' ? invalidLabel : error === 'tooLong' ? tooLongLabel : ''
})
const endMin = computed(() => card.period.startDate || today)
const endMax = computed(() => (card.period.startDate ? addDays(card.period.startDate, MAX_TRIP_DAYS - 1) : undefined))

function dateValue(event: Event): string {
  return (event.target as HTMLInputElement).value
}
</script>

<template>
  <PreferenceCardFrame
    :title="card.title"
    :icon="card.icon"
    :required-label="requiredLabel"
    :show-missing="card.showMissing"
  >
    <div class="grid gap-3 sm:grid-cols-2">
      <label class="block text-sm text-slate-300">
        {{ startLabel }}
        <input
          class="planner-date mt-1.5"
          type="date"
          required
          :min="today"
          :max="card.period.endDate || undefined"
          :value="card.period.startDate"
          :aria-label="startLabel"
          @input="emit('set-start', dateValue($event))"
        />
      </label>
      <label class="block text-sm text-slate-300">
        {{ endLabel }}
        <input
          class="planner-date mt-1.5"
          type="date"
          required
          :min="endMin"
          :max="endMax"
          :value="card.period.endDate"
          :aria-label="endLabel"
          @input="emit('set-end', dateValue($event))"
        />
      </label>
    </div>
    <p v-if="rangeError" class="mt-3 text-sm text-rose-300" role="alert">{{ rangeError }}</p>
  </PreferenceCardFrame>
</template>
