<script setup lang="ts">
import AccountShell from '~/components/Account/AccountShell.vue'
import StatusBadge from '~/components/Account/StatusBadge.vue'
import InvoiceCard from '~/components/Account/InvoiceCard.vue'
import { UNIT_LABELS } from '~/constants/checkout'
import type { MyTripDetail } from '~/types/account'
definePageMeta({ layout: 'planner' })
const route = useRoute()
const api = useApi()
const { locale, messages: m, money, date, count } = useAccountMessages()
const {
  data: trip,
  loading,
  failed,
  notFound,
  load,
} = useAccountResource<MyTripDetail>(`/me/trips/${String(route.params.id)}`)
const router = useRouter()
/** Arriving from "Save trip": confirm it once, then drop the flag so a refresh does not repeat it. */
const justSaved = ref(route.query.saved === '1')
onMounted(() => {
  if (justSaved.value) router.replace({ query: {} })
})
const busy = ref(false)
const actionError = ref(false)
const days = computed(() => trip.value?.plan?.days ?? trip.value?.itinerary?.days ?? [])
const selectedStays = computed(() => trip.value?.plan?.days.filter((day) => day.stay) ?? [])
const openCheckout = computed(() =>
  trip.value?.checkouts.find(
    (checkout) => checkout.status === 'open' && new Date(checkout.expires_at).getTime() > Date.now()
  )
)
async function resume() {
  if (!trip.value || busy.value) return
  busy.value = true
  actionError.value = false
  const { data } = await api.post<{ proposal_id: string }>(`/me/trips/${trip.value.id}/resume`)
  busy.value = false
  if (data) await navigateTo(`/plan/${data.proposal_id}`)
  else actionError.value = true
}
function unitLabel(unit: string | null) {
  return unit ? (UNIT_LABELS[unit]?.[locale.value] ?? unit) : ''
}
</script>

<template>
  <AccountShell :title="trip?.title ?? m.trips">
    <template #action><StatusBadge v-if="trip" :status="trip.status" /></template>
    <p v-if="loading" class="py-8 text-ink-muted" role="status">{{ m.loading }}</p>
    <div v-else-if="notFound" class="panel px-6 py-12 text-center" role="alert">
      <i class="pi pi-map mb-4 block text-3xl text-ink-subtle" aria-hidden="true" />
      <p class="font-semibold">{{ m.notFound }}</p>
      <p class="mt-2 text-sm text-ink-muted">{{ m.notFoundHint }}</p>
      <NuxtLink to="/trips" class="btn-secondary mt-6 px-4 py-2">
        <i class="pi pi-arrow-left" aria-hidden="true" />
        {{ m.backToTrips }}
      </NuxtLink>
    </div>
    <div v-else-if="failed || !trip" class="panel p-6" role="alert">
      <p>{{ m.genericError }}</p>
      <button class="btn-secondary mt-4 px-4 py-2" @click="load">{{ m.retry }}</button>
    </div>
    <template v-else>
      <p
        v-if="justSaved"
        class="mb-5 flex items-center gap-3 rounded-control bg-success-soft p-4 text-sm font-medium text-success"
        role="status"
      >
        <i class="pi pi-check-circle" aria-hidden="true" />
        <span class="flex-1">{{ m.saved }}</span>
        <button
          type="button"
          class="text-success/80 hover:text-success"
          :aria-label="m.dismiss"
          @click="justSaved = false"
        >
          <i class="pi pi-times" aria-hidden="true" />
        </button>
      </p>
      <section class="panel p-6">
        <div class="flex flex-wrap items-center justify-between gap-6">
          <div>
            <p class="flex items-center gap-2 font-medium">
              <i class="pi pi-calendar text-brand" aria-hidden="true" />
              {{ date(trip.start_date) }} — {{ date(trip.end_date) }}
            </p>
            <p class="mt-2 text-sm text-ink-muted">{{ count(trip.party.adults + trip.party.children, 'people') }}</p>
          </div>
          <div v-if="trip.plan" class="text-right">
            <p class="text-xs text-ink-muted">{{ m.estimated }}</p>
            <p class="mt-1 text-xl font-bold">{{ money(trip.plan.totals.total_mnt) }}</p>
          </div>
        </div>
        <p v-if="trip.plan?.summary" class="mt-5 border-t border-line pt-5 text-sm leading-relaxed text-ink-muted">
          {{ trip.plan.summary }}
        </p>
        <button
          v-if="trip.can_resume"
          class="btn-primary mt-5 px-5 py-3 disabled:opacity-60"
          :disabled="busy"
          @click="resume"
        >
          <i :class="busy ? 'pi pi-spinner pi-spin' : 'pi pi-arrow-right'" aria-hidden="true" />
          {{ m.resume }}
        </button>
        <NuxtLink v-else-if="openCheckout" :to="`/checkout/${openCheckout.id}`" class="btn-primary mt-5 px-5 py-3">
          {{ m.pay }}
          <i class="pi pi-arrow-right" aria-hidden="true" />
        </NuxtLink>
        <p v-if="actionError" class="mt-3 text-sm text-danger" role="alert">{{ m.genericError }}</p>
      </section>
      <section v-if="days.length" class="mt-9">
        <h2 class="mb-4 font-display text-xl font-bold">{{ m.itinerary }}</h2>
        <ol class="panel divide-y divide-line px-5">
          <li v-for="day in days" :key="day.day" class="flex items-center gap-4 py-4">
            <span
              class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-brand-soft text-sm font-semibold text-brand"
            >
              {{ day.day }}
            </span>
            <div>
              <p class="text-sm font-semibold">
                {{ trip.places[day.from_place_id]?.name ?? day.from_place_id }} →
                {{ trip.places[day.to_place_id]?.name ?? day.to_place_id }}
              </p>
              <p class="mt-1 text-xs text-ink-muted">{{ date(day.date) }}</p>
            </div>
          </li>
        </ol>
      </section>
      <section v-if="selectedStays.length && !trip.bookings.length" class="mt-9">
        <h2 class="mb-4 font-display text-xl font-bold">{{ m.stays }}</h2>
        <div class="grid gap-4 sm:grid-cols-2">
          <article v-for="day in selectedStays" :key="day.day" class="panel overflow-hidden">
            <img
              v-if="trip.stays[day.stay!.stay_id]?.cover_image_url"
              :src="trip.stays[day.stay!.stay_id]!.cover_image_url"
              alt=""
              class="h-36 w-full object-cover"
            />
            <div class="p-5">
              <h3 class="font-semibold">{{ trip.stays[day.stay!.stay_id]?.name ?? day.stay!.stay_id }}</h3>
              <p class="mt-2 text-sm text-ink-muted">
                {{ unitLabel(day.stay!.unit_type) }} · {{ count(day.stay!.units, 'rooms') }}
              </p>
              <p class="mt-2 text-sm text-ink-muted">{{ date(day.date) }} · {{ count(day.stay!.nights, 'nights') }}</p>
              <p class="mt-3 font-semibold">{{ money(day.stay!.total_mnt) }}</p>
            </div>
          </article>
        </div>
      </section>
      <section class="mt-9">
        <h2 class="mb-4 font-display text-xl font-bold">{{ m.bookings }}</h2>
        <p v-if="!trip.bookings.length" class="panel p-6 text-sm leading-relaxed text-ink-muted">{{ m.noBookings }}</p>
        <div v-else class="space-y-4">
          <article v-for="booking in trip.bookings" :key="booking.id" class="panel p-5 sm:p-6">
            <div class="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h3 class="text-lg font-semibold">
                  {{ (booking.stay_id && trip.stays[booking.stay_id]?.name) || m.bookings }}
                </h3>
                <p class="mt-1 text-sm text-ink-muted">
                  {{ unitLabel(booking.unit_type) }}
                  <template v-if="booking.units">· {{ count(booking.units, 'rooms') }}</template>
                </p>
              </div>
              <StatusBadge :status="booking.status" />
            </div>
            <dl class="mt-5 grid grid-cols-2 gap-4 border-t border-line pt-5 text-sm sm:grid-cols-4">
              <div v-if="booking.check_in">
                <dt class="text-ink-muted">{{ m.checkIn }}</dt>
                <dd class="mt-1">{{ date(booking.check_in) }}</dd>
              </div>
              <div v-if="booking.check_out">
                <dt class="text-ink-muted">{{ m.checkOut }}</dt>
                <dd class="mt-1">{{ date(booking.check_out) }}</dd>
              </div>
              <div v-if="booking.guests">
                <dt class="text-ink-muted">{{ m.guests }}</dt>
                <dd class="mt-1">{{ booking.guests }} · {{ count(booking.nights ?? 0, 'nights') }}</dd>
              </div>
              <div>
                <dt class="text-ink-muted">{{ m.total }}</dt>
                <dd class="mt-1 font-semibold">{{ money(booking.total_price_mnt) }}</dd>
              </div>
            </dl>
            <p class="mt-5 text-xs break-all text-ink-subtle">{{ m.bookingId }}: {{ booking.id }}</p>
          </article>
        </div>
      </section>
      <section v-if="trip.invoices.length" class="mt-9">
        <h2 class="mb-4 font-display text-xl font-bold">{{ m.invoices }}</h2>
        <div class="space-y-3">
          <InvoiceCard v-for="invoice in trip.invoices" :key="invoice.id" :invoice="invoice" :show-trip-link="false" />
        </div>
      </section>
    </template>
  </AccountShell>
</template>
