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
} = defineProps<{
  isListening: boolean
  /** The recording is being turned into text */
  isTranscribing?: boolean
  voiceStatusLabel: string
  requestLabel: string
  requestPlaceholder: string
  voiceButtonLabel: string
  sendLabel: string
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
    emit('submit')
  }
}

watch(tripRequest, () => nextTick(fitHeight))
onMounted(fitHeight)
</script>

<template>
  <div
    class="chat-bar flex min-h-16 items-end gap-1 rounded-[32px] border border-line bg-surface py-2 pr-2 pl-7 shadow-card transition-shadow focus-within:border-brand"
    :class="{ 'is-listening': isListening }"
  >
    <label for="trip-request" class="sr-only">{{ requestLabel }}</label>
    <textarea
      id="trip-request"
      ref="field"
      v-model="tripRequest"
      rows="1"
      class="min-h-12 flex-1 resize-none self-center border-0! bg-transparent! py-3 text-base leading-6 text-ink sm:text-lg shadow-none! outline-none! placeholder:text-ink-subtle"
      :placeholder="isListening || isTranscribing ? voiceStatusLabel : requestPlaceholder"
      @keydown="onKeydown"
    />

    <div v-if="isListening" class="flex h-12 items-center gap-1 px-1" aria-hidden="true">
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
        class="relative grid h-12 w-12 place-items-center rounded-full text-ink-muted transition-colors hover:bg-surface-muted hover:text-ink aria-pressed:bg-danger aria-pressed:text-white"
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
      class="grid h-12 w-12 shrink-0 place-items-center rounded-full bg-brand text-brand-contrast transition-[background-color,transform] hover:bg-brand-hover active:scale-95"
      :aria-label="sendLabel"
      :title="sendLabel"
      @click="emit('submit')"
    >
      <i class="pi pi-arrow-up text-lg" aria-hidden="true" />
    </button>
  </div>
</template>
