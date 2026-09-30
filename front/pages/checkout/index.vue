<script setup lang="ts">
/**
 * Demo entry until the agent creates checkouts itself: pick one of your trips, a stay with free units, hold it.
 */
import MongoliaMapBackdrop from '~/components/TripPlanner/MongoliaMapBackdrop.vue'
import { API_ENDPOINTS } from '~/constants'
import PlannerHeader from '~/components/TripPlanner/PlannerHeader.vue'
import { CHECKOUT_MESSAGES, UNIT_LABELS } from '~/constants/checkout'
import type { AppLocale } from '~/types/trip-planner'

definePageMeta({ layout: 'planner' })

interface TripItem {
  id: string
  title: string
  start_date: string
}
interface StayUnit {
  unit_type: string
  price_mnt: number
  price_basis: 'per_unit' | 'per_person'
  beds_per_unit: number
}
interface StayItem {
  id: string
  name: string
  aimag: string
  units: StayUnit[]
}

const api = useApi()
const locale = useState<AppLocale>('app-locale', () => 'mn')
const messages = computed(() => CHECKOUT_MESSAGES[locale.value])
const labels = computed(() =>
  locale.value === 'mn'
    ? {
        heading: 'Демо: буудал захиалах',
        trip: 'Аялал',
        date: 'Ирэх өдөр',
        nights: 'Шөнө',
        guests: 'Зочид',
        hold: 'Түр барих',
      }
    : { heading: 'Demo: book a stay', trip: 'Trip', date: 'Check-in', nights: 'Nights', guests: 'Guests', hold: 'Hold' }
)

const trips = ref<TripItem[]>([])
const stays = ref<StayItem[]>([])
const tripId = ref('')
const checkIn = ref('2026-10-03')
const nights = ref(1)
const guests = ref(2)
const busyKey = ref<string | null>(null)
const errorMessage = ref<string | null>(null)

async function loadStays() {
  const { data } = await api.get<StayItem[]>(API_ENDPOINTS.TRAVEL.STAYS, {
    query: { date: checkIn.value, limit: 12 },
    headers: { 'Accept-Language': locale.value },
  })
  stays.value = data ?? []
}

async function hold(stay: StayItem, unit: StayUnit) {
  busyKey.value = `${stay.id}:${unit.unit_type}`
  errorMessage.value = null
  const units = unit.price_basis === 'per_person' ? Math.ceil(guests.value / unit.beds_per_unit) : 1
  const { data, error } = await api.post<{ id: string }>(API_ENDPOINTS.BOOKINGS.CREATE_CHECKOUT(tripId.value), {
    stays: [
      {
        stay_id: stay.id,
        unit_type: unit.unit_type,
        check_in: checkIn.value,
        nights: nights.value,
        units,
        guests: guests.value,
      },
    ],
  })
  busyKey.value = null
  if (error || !data) {
    const detail = (error as { data?: { detail?: { code?: string; detail?: string } } } | null)?.data?.detail
    errorMessage.value = detail ? `${detail.code}: ${detail.detail ?? ''}` : (error?.message ?? 'error')
    return
  }
  await navigateTo(`/checkout/${data.id}`)
}

onMounted(async () => {
  const { data } = await api.get<TripItem[]>(API_ENDPOINTS.TRAVEL.MY_TRIPS, {
    headers: { 'Accept-Language': locale.value },
  })
  trips.value = data ?? []
  tripId.value = trips.value[0]?.id ?? ''
  await loadStays()
})
watch([checkIn, locale], loadStays)
</script>

<template>
  <div>
    <MongoliaMapBackdrop />
    <PlannerHeader :locale="locale" :language-group-label="messages.languageGroupLabel" @set-locale="locale = $event" />
    <main class="mx-auto max-w-3xl px-4 pt-10 pb-20">
      <h1 class="text-2xl font-bold tracking-tight">{{ labels.heading }}</h1>

      <div class="glass-panel mt-6 grid gap-3 rounded-2xl p-4 sm:grid-cols-4">
        <label class="text-sm sm:col-span-2">
          <span class="text-slate-400">{{ labels.trip }}</span>
          <select v-model="tripId" class="planner-date mt-1 w-full rounded-lg bg-slate-900 p-2">
            <option v-for="trip in trips" :key="trip.id" :value="trip.id">{{ trip.title }}</option>
          </select>
        </label>
        <label class="text-sm">
          <span class="text-slate-400">{{ labels.date }}</span>
          <input v-model="checkIn" type="date" class="planner-date mt-1 w-full rounded-lg bg-slate-900 p-2" />
        </label>
        <div class="grid grid-cols-2 gap-2 text-sm">
          <label>
            <span class="text-slate-400">{{ labels.nights }}</span>
            <input
              v-model.number="nights"
              type="number"
              min="1"
              max="7"
              class="planner-date mt-1 w-full rounded-lg bg-slate-900 p-2"
            />
          </label>
          <label>
            <span class="text-slate-400">{{ labels.guests }}</span>
            <input
              v-model.number="guests"
              type="number"
              min="1"
              max="10"
              class="planner-date mt-1 w-full rounded-lg bg-slate-900 p-2"
            />
          </label>
        </div>
      </div>

      <p v-if="errorMessage" class="mt-4 text-sm text-rose-300" role="alert">{{ errorMessage }}</p>

      <ul class="mt-6 space-y-3">
        <li v-for="stay in stays" :key="stay.id" class="glass-panel rounded-2xl p-4">
          <p class="font-semibold">
            {{ stay.name }}
            <span class="text-sm font-normal text-slate-400">· {{ stay.aimag }}</span>
          </p>
          <div class="mt-3 flex flex-wrap gap-2">
            <button
              v-for="unit in stay.units"
              :key="unit.unit_type"
              type="button"
              class="choice-chip rounded-full border border-slate-700 px-4 text-sm hover:border-emerald-400 disabled:opacity-50"
              :disabled="!tripId || busyKey !== null"
              @click="hold(stay, unit)"
            >
              <i
                v-if="busyKey === `${stay.id}:${unit.unit_type}`"
                class="pi pi-spinner pi-spin mr-1"
                aria-hidden="true"
              />
              {{ UNIT_LABELS[unit.unit_type]?.[locale] ?? unit.unit_type }} ·
              {{ new Intl.NumberFormat('mn-MN').format(unit.price_mnt) }} ₮ · {{ labels.hold }}
            </button>
          </div>
        </li>
      </ul>
    </main>
  </div>
</template>
