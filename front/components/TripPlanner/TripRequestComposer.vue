<script setup lang="ts">
import { VOICE_METER_DELAYS_MS } from '~/constants/tripPlanner'

/** One long chat-style bar: type or speak the trip, Enter (or the arrow) sends it to the planner */
const tripRequest = defineModel<string>('tripRequest', { required: true })

const {
  isListening,
  isTranscribing = false,
  voiceStatusLabel,
  requestLabel,
  requestPlaceholder,
  voiceButtonLabel,
  sendLabel,
  fieldId = 'trip-request',
  compact = false,
  disabled = false,
} = defineProps<{
  isListening: boolean
  /** The recording is being turned into text */
  isTranscribing?: boolean
  voiceStatusLabel: string
  requestLabel: string
  requestPlaceholder: string
  voiceButtonLabel: string
  sendLabel: string
  fieldId?: string
  /** A smaller bar, for the chat under a plan */
  compact?: boolean
  /** The agent is still answering: typing stays open, sending waits */
  disabled?: boolean
}>()

const emit = defineEmits<{
  'toggle-voice': []
  submit: []
}>()

const MAX_HEIGHT_PX = 220
const field = ref<HTMLTextAreaElement | null>(null)

/** Grows the field with its text, up to a few lines, then it scrolls */
function fitHeight() {
  const el = field.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = `${Math.min(el.scrollHeight, MAX_HEIGHT_PX)}px`
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
    event.preventDefault()
    if (!disabled) emit('submit')
  }
}

watch(tripRequest, () => nextTick(fitHeight))
onMounted(fitHeight)
</script>

<template>
  <div
    class="chat-bar flex items-end gap-1 border border-line bg-surface shadow-card transition-shadow focus-within:border-brand"
    :class="[
      { 'is-listening': isListening },
      compact ? 'min-h-12 rounded-[26px] py-1.5 pr-1.5 pl-5' : 'min-h-16 rounded-[32px] py-2 pr-2 pl-7',
    ]"
  >
    <label :for="fieldId" class="sr-only">{{ requestLabel }}</label>
    <textarea
      :id="fieldId"
      ref="field"
      v-model="tripRequest"
      rows="1"
      class="flex-1 resize-none self-center border-0! bg-transparent! leading-6 text-ink shadow-none! outline-none! placeholder:text-ink-subtle"
      :class="compact ? 'min-h-9 py-1.5 text-[0.95rem]' : 'min-h-12 py-3 text-base sm:text-lg'"
      :placeholder="isListening || isTranscribing ? voiceStatusLabel : requestPlaceholder"
      @keydown="onKeydown"
    />

    <div v-if="isListening" class="flex items-center gap-1 px-1" :class="compact ? 'h-9' : 'h-12'" aria-hidden="true">
      <span
        v-for="(delayMs, index) in VOICE_METER_DELAYS_MS"
        :key="index"
        class="eq-bar"
        :style="{ animationDelay: `${delayMs}ms` }"
      />
    </div>

    <div class="relative shrink-0">
      <span class="mic-ring absolute inset-0 rounded-full bg-danger/25 opacity-0" />
      <button
        type="button"
        class="relative grid place-items-center rounded-full text-ink-muted transition-colors hover:bg-surface-muted hover:text-ink aria-pressed:bg-danger aria-pressed:text-white"
        :class="compact ? 'h-9 w-9' : 'h-12 w-12'"
        :aria-pressed="isListening"
        :aria-busy="isTranscribing"
        :aria-label="isTranscribing ? voiceStatusLabel : voiceButtonLabel"
        :title="isTranscribing ? voiceStatusLabel : voiceButtonLabel"
        :disabled="isTranscribing"
        @click="emit('toggle-voice')"
      >
        <i
          :class="isTranscribing ? 'pi pi-spinner pi-spin' : isListening ? 'pi pi-stop' : 'pi pi-microphone'"
          class="text-lg"
          aria-hidden="true"
        />
      </button>
    </div>

    <!-- Like a chat app: the send arrow appears once there is something to send -->
    <button
      v-if="tripRequest.trim()"
      type="button"
      class="grid shrink-0 place-items-center rounded-full bg-brand text-brand-contrast transition-[background-color,transform] hover:bg-brand-hover active:scale-95 disabled:opacity-50"
      :class="compact ? 'h-9 w-9' : 'h-12 w-12'"
      :disabled="disabled"
      :aria-label="sendLabel"
      :title="sendLabel"
      @click="emit('submit')"
    >
      <i class="pi pi-arrow-up text-lg" aria-hidden="true" />
    </button>
  </div>
</template>
