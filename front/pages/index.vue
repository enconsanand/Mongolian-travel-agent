<script setup lang="ts">
import MongoliaMapBackdrop from '~/components/TripPlanner/MongoliaMapBackdrop.vue'
import PlanGenerationDialog from '~/components/TripPlanner/PlanGenerationDialog.vue'
import PlannerHeader from '~/components/TripPlanner/PlannerHeader.vue'
import PreferenceChipGroup from '~/components/TripPlanner/PreferenceChipGroup.vue'
import TravelPeriodCard from '~/components/TripPlanner/TravelPeriodCard.vue'
import TripRequestComposer from '~/components/TripPlanner/TripRequestComposer.vue'

definePageMeta({
  layout: 'planner',
  auth: false,
})

const {
  locale,
  messages,
  tripRequest,
  isListening,
  isPlanDialogOpen,
  preferenceErrorMessage,
  preferenceCards,
  voiceStatusLabel,
  planSearchSteps,
  planError,
  setLocale,
  selectPresetOption,
  setCustomPreference,
  setTravelPeriod,
  toggleVoiceInput,
  openPlanDialog,
  closePlanDialog,
} = useTripPlanner()

useHead(() => ({
  title: messages.value.documentTitle,
  htmlAttrs: { lang: locale.value },
}))
</script>

<template>
  <div>
    <MongoliaMapBackdrop />
    <PlannerHeader :locale="locale" :language-group-label="messages.languageGroupLabel" @set-locale="setLocale" />

    <main class="mx-auto max-w-4xl px-4 pb-20">
      <section class="pt-12 pb-8 text-center sm:pt-20">
        <h1 class="text-3xl leading-tight font-bold tracking-tight sm:text-5xl">
          {{ messages.heroTitle }}
        </h1>
        <p class="mt-4 text-sm text-slate-400 sm:text-base">
          {{ messages.heroSubtitle }}
        </p>
      </section>

      <TripRequestComposer
        v-model:trip-request="tripRequest"
        :is-listening="isListening"
        :voice-status-label="voiceStatusLabel"
        :request-label="messages.requestLabel"
        :request-placeholder="messages.requestPlaceholder"
        :voice-button-label="messages.voiceButtonLabel"
        :voice-support="messages.voiceSupport"
        @toggle-voice="toggleVoiceInput"
      />

      <section class="mt-6 grid gap-4 lg:grid-cols-2" :aria-label="messages.requiredSectionLabel">
        <template v-for="card in preferenceCards" :key="card.id">
          <TravelPeriodCard
            v-if="card.kind === 'period'"
            :card="card"
            :required-label="messages.required"
            :start-label="messages.periodStartLabel"
            :end-label="messages.periodEndLabel"
            :invalid-label="messages.periodInvalid"
            @set-start="setTravelPeriod('startDate', $event)"
            @set-end="setTravelPeriod('endDate', $event)"
          />
          <PreferenceChipGroup
            v-else
            :card="card"
            :required-label="messages.required"
            :custom-value-label="messages.customValue"
            @select-preset="selectPresetOption(card.id, $event)"
            @set-custom="setCustomPreference(card.id, $event)"
          />
        </template>
      </section>

      <button
        type="button"
        class="generate-button mt-8 flex w-full items-center justify-center gap-2 rounded-xl py-4 text-base font-semibold text-slate-900 transition-shadow sm:text-lg"
        :aria-describedby="preferenceErrorMessage ? 'preference-error' : undefined"
        @click="openPlanDialog"
      >
        <i class="pi pi-sparkles text-lg" aria-hidden="true" />
        {{ messages.generate }}
      </button>
      <p
        v-if="preferenceErrorMessage"
        id="preference-error"
        class="mt-3 text-center text-sm text-rose-300"
        role="alert"
      >
        {{ preferenceErrorMessage }}
      </p>
    </main>

    <PlanGenerationDialog
      :open="isPlanDialogOpen"
      :title="messages.buildingTitle"
      :hint="messages.buildingHint"
      :close-label="messages.close"
      :cancel-label="messages.cancel"
      :dialog-label="messages.dialogLabel"
      :steps="planSearchSteps"
      :error-message="planError ? messages.errors[planError] : null"
      :retry-label="messages.retry"
      @close="closePlanDialog"
      @retry="openPlanDialog"
    />
  </div>
</template>
