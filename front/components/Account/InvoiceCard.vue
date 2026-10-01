<script setup lang="ts">
import type { Invoice } from '~/types/account'
import StatusBadge from './StatusBadge.vue'
const { showTripLink = true } = defineProps<{ invoice: Invoice; showTripLink?: boolean }>()
const { messages: m, money, date } = useAccountMessages()
</script>

<template>
  <details class="panel group p-5">
    <summary
      class="flex cursor-pointer list-none flex-wrap items-center justify-between gap-4 [&::-webkit-details-marker]:hidden"
    >
      <div class="flex min-w-0 items-center gap-3">
        <span class="flex h-10 w-10 shrink-0 items-center justify-center rounded-control bg-brand-soft text-brand">
          <i class="pi pi-receipt" aria-hidden="true" />
        </span>
        <div class="min-w-0">
          <p class="font-semibold break-words">{{ invoice.trip_title }}</p>
          <p class="mt-1 text-xs text-ink-muted">{{ m.invoice }} · {{ invoice.id }}</p>
        </div>
      </div>
      <div class="ml-auto flex items-center gap-3">
        <div class="text-right">
          <p class="mb-2 font-semibold">{{ money(invoice.amount_mnt) }}</p>
          <StatusBadge :status="invoice.status" />
        </div>
        <i class="pi pi-chevron-down text-xs text-ink-subtle group-open:rotate-180" aria-hidden="true" />
      </div>
    </summary>
    <div class="mt-5 border-t border-line pt-5 text-sm">
      <dl class="grid gap-4 sm:grid-cols-2">
        <div>
          <dt class="text-ink-muted">{{ m.reference }}</dt>
          <dd class="mt-1 break-all">{{ invoice.reference }}</dd>
        </div>
        <div>
          <dt class="text-ink-muted">{{ m.method }}</dt>
          <dd class="mt-1 uppercase">{{ invoice.provider }}</dd>
        </div>
        <div v-if="invoice.paid_at">
          <dt class="text-ink-muted">{{ m.paidAt }}</dt>
          <dd class="mt-1">{{ date(invoice.paid_at) }}</dd>
        </div>
      </dl>
      <ul v-if="invoice.lines.length" class="mt-5 divide-y divide-line">
        <li v-for="(line, index) in invoice.lines" :key="index" class="flex justify-between gap-4 py-3">
          <span>{{ line.label }} × {{ line.qty }}</span>
          <span class="shrink-0">{{ money(line.total_mnt) }}</span>
        </li>
      </ul>
      <NuxtLink
        v-if="showTripLink"
        :to="`/trips/${invoice.trip_id}`"
        class="mt-4 inline-flex items-center gap-2 font-semibold text-brand"
      >
        {{ m.details }}
        <i class="pi pi-arrow-right text-xs" aria-hidden="true" />
      </NuxtLink>
    </div>
  </details>
</template>
