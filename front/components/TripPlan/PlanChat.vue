<script setup lang="ts">
import BrandMark from '~/components/Common/BrandMark.vue'
import TripRequestComposer from '~/components/TripPlanner/TripRequestComposer.vue'
import { PLAN_MESSAGES } from '~/constants/tripPlan'
import { TRIP_PLANNER_MESSAGES } from '~/constants/tripPlanner'
import type { AppLocale } from '~/types/trip-planner'
import { voiceStatusText } from '~/composables/useVoiceInput'

export interface PlanChatEntry {
  id: number
  role: 'user' | 'agent'
  text: string
  failed?: boolean
}

/**
 * Talking to the planner under the plan: each message revises the plan in place (route, stops, nights), and the
 * conversation stays in a short log above the bar so the plan itself is never covered for long.
 */
const draft = defineModel<string>({ required: true })

const { locale, entries, working, earlierChanges } = defineProps<{
  locale: AppLocale
  entries: PlanChatEntry[]
  /** The planner is answering the last message */
  working: boolean
  /** Changes asked before this visit, from the plan itself */
  earlierChanges: string[]
}>()

const emit = defineEmits<{ send: [text: string] }>()

const messages = computed(() => PLAN_MESSAGES[locale])
const voiceMessages = computed(() => TRIP_PLANNER_MESSAGES[locale])
const open = ref(true)
const scroller = ref<HTMLElement | null>(null)

// Speech is added to whatever is already typed, like on the home page
const voice = useVoiceInput((text) => {
  draft.value = draft.value.trim() ? `${draft.value.trim()} ${text}` : text
})
const isListening = computed(() => voice.state.value === 'recording')
const voiceStatusLabel = computed(() =>
  voiceStatusText(voice.state.value, voiceMessages.value, messages.value.chatPlaceholder)
)

function send() {
  const text = draft.value.trim()
  if (!text || working) return
  emit('send', text)
}

// A new message opens the log and scrolls to it
watch(
  () => [entries.length, working],
  () => {
    open.value = true
    nextTick(() => scroller.value?.scrollTo({ top: scroller.value.scrollHeight, behavior: 'smooth' }))
  }
)

const hasLog = computed(() => entries.length > 0 || working || earlierChanges.length > 0)
</script>

<template>
  <div>
    <div v-if="hasLog" class="mb-2 flex justify-end">
      <button
        type="button"
        class="flex items-center gap-1.5 text-xs text-ink-muted hover:text-ink"
        :aria-expanded="open"
        @click="open = !open"
      >
        {{ open ? messages.chatHide : messages.chatShow }}
        <i :class="open ? 'pi pi-chevron-down' : 'pi pi-chevron-up'" class="text-[0.65rem]" aria-hidden="true" />
      </button>
    </div>

    <div v-if="hasLog && open" ref="scroller" class="mb-3 max-h-[28vh] overflow-y-auto overscroll-contain pr-1">
      <p v-if="earlierChanges.length && !entries.length" class="text-xs text-ink-muted">
        {{ messages.changesSoFar }}: {{ earlierChanges.join(' · ') }}
      </p>
      <ol class="flex flex-col gap-2.5" aria-live="polite">
        <li v-for="entry in entries" :key="entry.id" class="chat-in flex">
          <p
            v-if="entry.role === 'user'"
            class="ml-auto max-w-[85%] rounded-[18px_6px_18px_18px] bg-brand px-3.5 py-2 text-sm whitespace-pre-line text-brand-contrast"
          >
            {{ entry.text }}
          </p>
          <div v-else class="flex max-w-[92%] gap-2">
            <BrandMark class="mt-0.5 h-6 w-6 shrink-0" />
            <p
              class="rounded-[6px_18px_18px_18px] px-3.5 py-2 text-sm leading-relaxed"
              :class="entry.failed ? 'bg-danger-soft text-danger' : 'border border-line bg-surface'"
            >
              {{ entry.text }}
            </p>
          </div>
        </li>
        <li v-if="working" class="flex items-center gap-2" :aria-label="messages.revising">
          <BrandMark class="h-6 w-6 shrink-0" />
          <span
            class="typing-dots flex gap-1 rounded-full border border-line bg-surface px-3.5 py-2.5"
            aria-hidden="true"
          >
            <span />
            <span />
            <span />
          </span>
          <span class="text-xs text-ink-muted">{{ messages.revising }}</span>
        </li>
      </ol>
    </div>

    <TripRequestComposer
      v-model:trip-request="draft"
      field-id="plan-chat"
      compact
      :disabled="working"
      :is-listening="isListening"
      :voice-status-label="voiceStatusLabel"
      :request-label="messages.reviseLabel"
      :request-placeholder="voiceStatusLabel"
      :voice-button-label="voiceMessages.voiceButtonLabel"
      :send-label="messages.chatSend"
      @toggle-voice="voice.toggle()"
      @submit="send"
    />
  </div>
</template>
