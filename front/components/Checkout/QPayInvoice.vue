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
  <section class="panel p-6 text-center" aria-live="polite">
    <h2 class="text-lg font-semibold">{{ messages.payTitle }}</h2>
    <p class="mt-1 text-sm text-ink-muted">{{ messages.payHint }}</p>

    <!-- eslint-disable-next-line vue/no-v-html -->
    <div v-if="qrSvg" class="mx-auto mt-5 w-56 rounded-control border border-line bg-white p-2" v-html="qrSvg" />

    <ul v-if="payment.deeplinks.length" class="mt-5 flex flex-wrap justify-center gap-2">
      <li v-for="link in payment.deeplinks" :key="link.link">
        <!-- Bank apps open by their own scheme; the simulator's are web pages, so keep the checkout open -->
        <a
          :href="link.link"
          :target="link.link.startsWith('http') ? '_blank' : undefined"
          rel="noopener"
          class="choice-chip inline-flex items-center text-sm"
        >
          {{ link.name }}
        </a>
      </li>
    </ul>

    <p class="mt-5 flex items-center justify-center gap-2 text-sm text-ink-muted">
      <i class="pi pi-spinner pi-spin" aria-hidden="true" />
      {{ messages.waiting }}
    </p>

    <button
      v-if="canSimulate"
      type="button"
      class="btn-secondary mt-4 border-dashed px-4 py-2 text-sm"
      @click="emit('simulate')"
    >
      {{ messages.simPay }}
    </button>
  </section>
</template>
