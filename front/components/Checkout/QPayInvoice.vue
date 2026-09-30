<script setup lang="ts">
import { renderSVG } from 'uqr'
import type { CheckoutMessages } from '~/constants/checkout'
import type { PaymentView } from '~/types/checkout'

const { payment, messages, canSimulate } = defineProps<{
  payment: PaymentView
  messages: CheckoutMessages
  canSimulate: boolean
}>()

const emit = defineEmits<{ simulate: [] }>()

// The SVG is drawn locally from the QR text (rects only, no text from the payload is embedded)
const qrSvg = computed(() => (payment.qr_text ? renderSVG(payment.qr_text, { border: 2 }) : ''))
</script>

<template>
  <section class="glass-panel rounded-2xl p-6 text-center" aria-live="polite">
    <h2 class="text-lg font-semibold">{{ messages.payTitle }}</h2>
    <p class="mt-1 text-sm text-slate-400">{{ messages.payHint }}</p>

    <!-- eslint-disable-next-line vue/no-v-html -->
    <div v-if="qrSvg" class="mx-auto mt-5 w-56 rounded-xl bg-white p-2" v-html="qrSvg" />

    <ul v-if="payment.deeplinks.length" class="mt-5 flex flex-wrap justify-center gap-2">
      <li v-for="link in payment.deeplinks" :key="link.link">
        <a
          :href="link.link"
          class="choice-chip inline-flex items-center rounded-full border border-slate-700 px-4 text-sm"
        >
          {{ link.name }}
        </a>
      </li>
    </ul>

    <p class="mt-5 flex items-center justify-center gap-2 text-sm text-cyan-300">
      <i class="pi pi-spinner pi-spin" aria-hidden="true" />
      {{ messages.waiting }}
    </p>

    <button
      v-if="canSimulate"
      type="button"
      class="mt-4 rounded-xl border border-dashed border-slate-600 px-4 py-2 text-sm text-slate-300 hover:border-emerald-400"
      @click="emit('simulate')"
    >
      {{ messages.simPay }}
    </button>
  </section>
</template>
