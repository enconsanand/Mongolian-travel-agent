<script setup lang="ts">
import AccountShell from '~/components/Account/AccountShell.vue'
import InvoiceCard from '~/components/Account/InvoiceCard.vue'
import type { Profile, Invoice } from '~/types/account'
definePageMeta({ layout: 'planner' })
const { messages: m, contact } = useAccountMessages()
const { data: profile, loading, failed, load } = useAccountResource<Profile>('/auth/me')
const {
  data: invoices,
  loading: invoicesLoading,
  failed: invoicesFailed,
  load: reloadInvoices,
} = useAccountResource<Invoice[]>('/me/invoices')
const auth = useAuth()
</script>

<template>
  <AccountShell :title="m.profile" :subtitle="m.accountHint">
    <template #action>
      <NuxtLink to="/trips" class="btn-secondary px-4 py-2.5 text-sm">
        <i class="pi pi-compass" aria-hidden="true" />
        {{ m.trips }}
      </NuxtLink>
    </template>
    <p v-if="loading" class="py-8 text-ink-muted" role="status">{{ m.loading }}</p>
    <div v-else-if="failed" class="panel p-6" role="alert">
      <p>{{ m.genericError }}</p>
      <button class="btn-secondary mt-4 px-4 py-2" @click="load">{{ m.retry }}</button>
    </div>
    <section v-else-if="profile" class="panel p-6 sm:p-8">
      <div class="flex items-center gap-4">
        <div
          class="flex h-16 w-16 shrink-0 items-center justify-center rounded-full bg-brand-soft font-display text-2xl text-brand"
        >
          {{ profile.first_name.slice(0, 1).toUpperCase() }}
        </div>
        <div>
          <h2 class="text-xl font-semibold">{{ profile.first_name }} {{ profile.last_name }}</h2>
          <p class="mt-1 text-sm break-all text-ink-muted">{{ profile.email || contact(profile.phone ?? '') }}</p>
        </div>
      </div>
      <dl class="mt-7 grid gap-6 border-t border-line pt-6 sm:grid-cols-2">
        <div>
          <dt class="text-sm text-ink-muted">{{ m.email }}</dt>
          <dd class="mt-2 break-all font-medium">{{ profile.email || m.notProvided }}</dd>
        </div>
        <div>
          <dt class="text-sm text-ink-muted">{{ m.phone }}</dt>
          <dd class="mt-2 font-medium">{{ profile.phone ? contact(profile.phone) : m.notProvided }}</dd>
        </div>
      </dl>
      <button class="mt-7 inline-flex items-center gap-2 text-sm text-ink-muted hover:text-ink" @click="auth.logout">
        <i class="pi pi-sign-out" aria-hidden="true" />
        {{ m.logout }}
      </button>
    </section>
    <section id="invoices" class="mt-10">
      <h2 class="font-display text-xl font-bold">{{ m.invoices }}</h2>
      <p class="mt-2 text-sm text-ink-muted">{{ m.invoiceHint }}</p>
      <p v-if="invoicesLoading" class="mt-5 text-ink-muted" role="status">{{ m.loading }}</p>
      <div v-else-if="invoicesFailed" class="panel mt-5 p-6" role="alert">
        <p>{{ m.genericError }}</p>
        <button class="btn-secondary mt-4 px-4 py-2" @click="reloadInvoices">{{ m.retry }}</button>
      </div>
      <div v-else-if="!invoices?.length" class="panel mt-5 p-8 text-center text-sm text-ink-muted">
        <i class="pi pi-receipt mb-3 block text-2xl" aria-hidden="true" />
        {{ m.emptyInvoices }}
      </div>
      <div v-else class="mt-5 space-y-3">
        <InvoiceCard v-for="invoice in invoices" :key="invoice.id" :invoice="invoice" />
      </div>
    </section>
  </AccountShell>
</template>
