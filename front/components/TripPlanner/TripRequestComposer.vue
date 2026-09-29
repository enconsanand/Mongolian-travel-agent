<script setup lang="ts">
import { VOICE_METER_DELAYS_MS } from '~/constants/tripPlanner'

const tripRequest = defineModel<string>('tripRequest', { required: true })

const { isListening, voiceStatusLabel, requestLabel, requestPlaceholder, voiceButtonLabel, voiceSupport } =
  defineProps<{
    isListening: boolean
    voiceStatusLabel: string
    requestLabel: string
    requestPlaceholder: string
    voiceButtonLabel: string
    voiceSupport: string
  }>()

const emit = defineEmits<{
  'toggle-voice': []
}>()
</script>

<template>
  <section class="glass-panel rounded-2xl p-4 shadow-2xl shadow-black/40 sm:p-6">
    <label for="trip-request" class="sr-only">{{ requestLabel }}</label>
    <textarea
      id="trip-request"
      v-model="tripRequest"
      rows="5"
      class="planner-field text-sm placeholder:text-slate-500 sm:text-base"
      :placeholder="requestPlaceholder"
    />

    <div class="mt-4 flex items-center gap-4">
      <div class="relative shrink-0" :class="{ 'is-listening': isListening }">
        <span class="mic-ring absolute inset-0 rounded-full bg-emerald-400/30" />
        <button
          type="button"
          class="mic-button relative grid h-16 w-16 place-items-center rounded-full bg-linear-to-br from-emerald-400 to-cyan-500 text-slate-900 shadow-[0_0_28px_rgba(52,211,153,0.55)]"
          :aria-pressed="isListening"
          :aria-label="voiceButtonLabel"
          @click="emit('toggle-voice')"
        >
          <i class="pi pi-microphone text-2xl" aria-hidden="true" />
        </button>
      </div>
      <div class="min-w-0">
        <div class="text-sm font-medium" aria-live="polite">{{ voiceStatusLabel }}</div>
        <div v-if="isListening" class="my-1 flex h-6 items-end gap-1">
          <span
            v-for="(delayMs, index) in VOICE_METER_DELAYS_MS"
            :key="index"
            class="eq-bar"
            :style="{ animationDelay: `${delayMs}ms` }"
          />
        </div>
        <div class="mt-0.5 flex items-center gap-1.5 text-xs text-emerald-300/90">
          <i class="pi pi-verified text-sm" aria-hidden="true" />
          {{ voiceSupport }}
        </div>
      </div>
    </div>
  </section>
</template>
