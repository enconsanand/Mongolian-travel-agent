<script setup lang="ts">
import AccountShell from '~/components/Account/AccountShell.vue'
import StatusBadge from '~/components/Account/StatusBadge.vue'
import type { MyTrip } from '~/types/account'
definePageMeta({ layout: 'planner' })
const { messages: m, money, date, count } = useAccountMessages()
const { data: trips, loading, failed, load } = useAccountResource<MyTrip[]>('/me/trips')
</script>

<template>
  <AccountShell :title="m.trips" :subtitle="m.tripsHint">
    <template #action>
      <NuxtLink to="/" class="btn-primary px-4 py-2.5 text-sm">
        <i class="pi pi-plus" aria-hidden="true" />
        {{ m.newTrip }}
      </NuxtLink>
    </template>
    <p v-if="loading" class="py-8 text-ink-muted" role="status">{{ m.loading }}</p>
    <div v-else-if="failed" class="panel p-6" role="alert">
      <p>{{ m.genericError }}</p>
      <button class="btn-secondary mt-4 px-4 py-2" @click="load">{{ m.retry }}</button>
    </div>
    <section v-else-if="!trips?.length" class="panel px-6 py-16 text-center">
      <span
        class="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-full bg-brand-soft text-2xl text-brand"
      >
        <i class="pi pi-compass" aria-hidden="true" />
      </span>
      <h2 class="font-display text-xl font-bold">{{ m.emptyTrips }}</h2>
      <p class="mt-3 text-sm text-ink-muted">{{ m.emptyTripsHint }}</p>
      <NuxtLink to="/" class="btn-primary mt-7 px-5 py-3">
        {{ m.newTrip }}
        <i class="pi pi-arrow-right" aria-hidden="true" />
      </NuxtLink>
    </section>
    <div v-else class="grid gap-5 sm:grid-cols-2">
      <NuxtLink
        v-for="trip in trips"
        :key="trip.id"
        :to="`/trips/${trip.id}`"
        class="panel group overflow-hidden transition-transform hover:-translate-y-1"
      >
        <div class="relative h-44 bg-brand-soft">
          <img
            v-if="trip.cover_image_url"
            :src="trip.cover_image_url"
            alt=""
            class="h-full w-full object-cover"
            loading="lazy"
          />
          <div v-else class="flex h-full items-center justify-center text-4xl text-brand">
            <i class="pi pi-map" aria-hidden="true" />
          </div>
          <div class="absolute top-4 left-4"><StatusBadge :status="trip.status" /></div>
        </div>
        <div class="p-5 sm:p-6">
          <h2 class="font-display text-xl font-bold">{{ trip.title }}</h2>
          <p v-if="trip.route?.length" class="mt-3 flex items-start gap-2 text-sm text-ink-muted">
            <i class="pi pi-map-marker mt-0.5" aria-hidden="true" />
            <span class="line-clamp-2">{{ trip.route.join(' → ') }}</span>
          </p>
          <p class="mt-3 flex items-center gap-2 text-sm text-ink-muted">
            <i class="pi pi-calendar" aria-hidden="true" />
            {{ date(trip.start_date) }} — {{ date(trip.end_date) }}
          </p>
          <p class="mt-2 flex items-center gap-2 text-sm text-ink-muted">
            <i class="pi pi-users" aria-hidden="true" />
            {{ count(trip.party.adults + trip.party.children, 'people') }}
          </p>
          <div class="mt-5 flex items-center justify-between gap-3 border-t border-line pt-4">
            <span class="text-sm font-semibold">{{ trip.total_mnt == null ? '' : money(trip.total_mnt) }}</span>
            <span class="inline-flex items-center gap-2 text-sm font-semibold text-brand">
              {{ m.details }}
              <i class="pi pi-arrow-right text-xs" aria-hidden="true" />
            </span>
          </div>
        </div>
      </NuxtLink>
    </div>
  </AccountShell>
</template>
