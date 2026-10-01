<script setup lang="ts">
import MandateApproval from '~/components/Checkout/MandateApproval.vue'
import QPayInvoice from '~/components/Checkout/QPayInvoice.vue'
import PlannerHeader from '~/components/TripPlanner/PlannerHeader.vue'
import { CHECKOUT_MESSAGES } from '~/constants/checkout'

definePageMeta({ layout: 'planner' })

const route = useRoute()
const { messages: accountMessages } = useAccountMessages()
const locale = useAppLocale()
const messages = computed(() => CHECKOUT_MESSAGES[locale.value])
const { stage, checkout, verified, payment, errorMessage, canSimulate, load, approve, simulatePayment } =
  useCheckoutPayment(String(route.params.id))

onMounted(load)
useHead(() => ({ title: messages.value.title, htmlAttrs: { lang: locale.value } }))
</script>

<template>
  <div>
    <PlannerHeader :locale="locale" :language-group-label="messages.languageGroupLabel" @set-locale="locale = $event" />

    <main class="mx-auto max-w-lg px-4 pt-10 pb-20">
      <h1 class="text-2xl font-semibold sm:text-3xl">{{ messages.title }}</h1>
      <p class="mt-2 text-sm text-ink-muted">{{ messages.subtitle }}</p>

      <div class="mt-6">
        <p v-if="stage === 'loading'" class="text-ink-muted">{{ messages.loading }}</p>

        <p v-else-if="stage === 'untrusted'" class="panel p-6 text-danger" role="alert">
          <i class="pi pi-exclamation-triangle mr-2" aria-hidden="true" />
          {{ messages.untrusted }}
        </p>

        <MandateApproval
          v-else-if="(stage === 'review' || stage === 'signing') && verified"
          :claims="verified.claims"
          :locale="locale"
          :messages="messages"
          :busy="stage === 'signing'"
          @approve="approve"
        />

        <QPayInvoice
          v-else-if="stage === 'paying' && payment"
          :payment="payment"
          :messages="messages"
          :can-simulate="canSimulate"
          @simulate="simulatePayment"
        />

        <section v-else class="panel p-6 text-center" aria-live="polite">
          <i
            class="text-4xl"
            :class="stage === 'booked' ? 'pi pi-check-circle text-success' : 'pi pi-clock text-ink-muted'"
            aria-hidden="true"
          />
          <h2 class="mt-3 text-lg font-semibold">{{ messages[stage as 'booked' | 'expired' | 'failed'] }}</h2>
          <p class="mt-1 text-sm text-ink-muted">
            {{ messages[`${stage}Hint` as 'bookedHint' | 'expiredHint' | 'failedHint'] }}
          </p>
        </section>

        <!-- Once the checkout has settled, the trip page is where the booking and invoice live -->
        <NuxtLink
          v-if="checkout && ['booked', 'expired', 'failed'].includes(stage)"
          :to="`/trips/${checkout.trip_id}`"
          class="mt-5 w-full px-5 py-3"
          :class="stage === 'booked' ? 'btn-primary' : 'btn-secondary'"
        >
          {{ accountMessages.viewTrip }}
          <i class="pi pi-arrow-right" aria-hidden="true" />
        </NuxtLink>

        <p v-if="errorMessage && stage !== 'untrusted'" class="mt-4 text-center text-sm text-danger" role="alert">
          {{ messages.error }}: {{ errorMessage }}
        </p>
      </div>
    </main>
  </div>
</template>
