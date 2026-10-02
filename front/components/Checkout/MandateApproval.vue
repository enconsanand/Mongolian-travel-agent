<script setup lang="ts">
/**
 * The AP2 trusted surface: renders only what the merchant signed (verified claims), never agent or LLM text, and
 * the Approve button is the only way a Payment Mandate gets signed.
 */
import { MERCHANT_NAME, UNIT_LABELS, type CheckoutMessages } from '~/constants/checkout'
import type { InstrumentType } from '~/types/checkout'
import type { AppLocale } from '~/types/trip-planner'
import type { CheckoutClaims } from '~/utils/ap2'
import { formatMnt } from '~/utils/tripPlan'

const { claims, locale, messages, busy } = defineProps<{
  claims: CheckoutClaims
  locale: AppLocale
  messages: CheckoutMessages
  busy: boolean
}>()

const emit = defineEmits<{ approve: [instrument: InstrumentType] }>()

const instrument = ref<InstrumentType>('qpay_qr')
const secondsLeft = ref(0)
let timer: ReturnType<typeof setInterval> | null = null

const money = (mnt: number) => formatMnt(mnt, locale)

/** One row per stay and unit type, with its nights listed. */
const stays = computed(() => {
  const groups = new Map<string, { name: string; unit: string; nights: string[]; total: number; qty: number }>()
  for (const line of claims.lines) {
    const key = `${line.ref_id}:${line.unit_type ?? ''}`
    const group = groups.get(key) ?? {
      name: line.label[locale],
      unit: UNIT_LABELS[line.unit_type ?? '']?.[locale] ?? line.unit_type ?? '',
      nights: [],
      total: 0,
      qty: line.qty,
    }
    if (line.date) group.nights.push(line.date)
    group.total += line.total_mnt
    groups.set(key, group)
  }
  return [...groups.values()]
})

const totalMnt = computed(() => claims.total.amount / 100)
const countdown = computed(() => {
  const s = Math.max(0, secondsLeft.value)
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
})

function tick() {
  secondsLeft.value = claims.exp - Math.floor(Date.now() / 1000)
}

onMounted(() => {
  tick()
  timer = setInterval(tick, 1000)
})
onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<template>
  <section class="panel p-6" aria-labelledby="mandate-title">
    <p class="flex items-center gap-2 text-xs font-medium text-success">
      <i class="pi pi-verified" aria-hidden="true" />
      {{ messages.verified }}
    </p>

    <ul class="mt-4 divide-y divide-line">
      <li v-for="stay in stays" :key="stay.name + stay.unit" class="py-3">
        <div class="flex items-start justify-between gap-4">
          <div>
            <p class="font-semibold">{{ stay.name }}</p>
            <p class="text-sm text-ink-muted">
              {{ stay.unit }} · {{ stay.nights.length }} {{ messages.nights }} · {{ stay.nights.join(', ') }}
            </p>
          </div>
          <p class="shrink-0 font-semibold tabular-nums">{{ money(stay.total) }}</p>
        </div>
      </li>
    </ul>

    <dl class="mt-4 space-y-2 border-t border-line pt-4 text-sm">
      <div class="flex justify-between">
        <dt class="text-ink-muted">{{ messages.payee }}</dt>
        <dd>{{ MERCHANT_NAME }}</dd>
      </div>
      <div class="flex justify-between">
        <dt class="text-ink-muted">{{ messages.expiresIn }}</dt>
        <dd class="tabular-nums" :class="secondsLeft < 120 ? 'text-danger' : ''">{{ countdown }}</dd>
      </div>
      <div class="flex items-baseline justify-between pt-2 text-lg">
        <dt id="mandate-title" class="font-semibold">{{ messages.total }}</dt>
        <dd class="font-bold tabular-nums">{{ money(totalMnt) }}</dd>
      </div>
    </dl>

    <fieldset class="mt-6">
      <legend class="mb-2 text-sm text-ink-muted">{{ messages.instrument }}</legend>
      <div class="grid grid-cols-2 gap-2">
        <label
          v-for="option in ['qpay_qr', 'card'] as const"
          :key="option"
          class="choice-chip flex items-center justify-center gap-2 px-3 text-sm"
          :data-active="instrument === option"
        >
          <input v-model="instrument" type="radio" name="instrument" :value="option" class="sr-only" />
          <i :class="option === 'qpay_qr' ? 'pi pi-qrcode' : 'pi pi-credit-card'" aria-hidden="true" />
          {{ option === 'qpay_qr' ? messages.qpay : messages.card }}
        </label>
      </div>
    </fieldset>

    <button
      type="button"
      class="btn-primary mt-6 w-full py-3.5 disabled:opacity-60"
      :disabled="busy || secondsLeft <= 0"
      @click="emit('approve', instrument)"
    >
      <i :class="busy ? 'pi pi-spinner pi-spin' : 'pi pi-lock'" aria-hidden="true" />
      {{ busy ? messages.signing : messages.approve }}
    </button>
    <p class="mt-3 text-center text-xs text-ink-muted">{{ messages.approveNote }}</p>
  </section>
</template>
