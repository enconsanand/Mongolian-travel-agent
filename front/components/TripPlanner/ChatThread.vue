<script setup lang="ts">
import BrandMark from '~/components/Common/BrandMark.vue'
import ChatPlanCard from '~/components/TripPlanner/ChatPlanCard.vue'
import ChatSlotChoices from '~/components/TripPlanner/ChatSlotChoices.vue'
import type { AppLocale, TripPlannerMessages } from '~/types/trip-planner'
import type { ChatMessage } from '~/composables/useTripPlanner'

/** The conversation with the agent, in a box of fixed height that keeps its newest message in view */
const { chat, locale, messages, typing, canGenerate, pendingSlot, defaultStart, defaultEnd } = defineProps<{
  chat: ChatMessage[]
  locale: AppLocale
  messages: TripPlannerMessages
  /** The agent is about to answer: show its typing dots */
  typing: boolean
  /** Every required answer is in, so the plan button may be pressed */
  canGenerate: boolean
  /** The question the choices under the latest ask belong to */
  pendingSlot: 'place' | 'guests' | 'dates' | 'budget' | null
  defaultStart: string
  defaultEnd: string
}>()

const emit = defineEmits<{ retry: []; generate: []; pick: [text: string] }>()

function showsNoExtra(message: ChatMessage): boolean {
  if (canGenerate || message.role !== 'agent' || message.kind !== 'extra') return false
  const last = [...chat].reverse().find((item) => item.role === 'agent' && item.kind === 'extra')
  return last?.id === message.id
}

function choiceSlot(message: ChatMessage): 'place' | 'guests' | 'dates' | 'budget' | null {
  if (typing || message.role !== 'agent' || message.kind !== 'ask' || message.slot !== pendingSlot) return null
  const lastAsk = [...chat].reverse().find((item) => item.role === 'agent' && item.kind === 'ask')
  return lastAsk?.id === message.id ? message.slot : null
}

/** The agent's line in the language selected now, including questions asked before the switch */
function agentText(message: ChatMessage): string {
  if (message.role === 'user') return message.text
  const chat = messages.chat
  if (message.kind === 'ask') {
    const question = chat.ask[message.slot]
    return message.deflect ? `${chat.offTopic} ${question}` : question
  }
  if (message.kind === 'extra') return message.deflect ? `${chat.offTopic} ${chat.extra}` : chat.extra
  if (message.kind === 'ready') return chat.ready
  if (message.kind === 'aside') return chat.offTopicReady
  if (message.kind === 'working') return message.phase === 'revising' ? chat.revising : chat.planning
  if (message.kind === 'plan') return message.revision ? chat.revised : chat.planned
  return message.code === 'planner_unavailable' ? messages.errors.planner_unavailable : messages.errors.error
}

const scroller = ref<HTMLElement | null>(null)

watch(
  () => [chat.length, chat.at(-1), typing],
  () => nextTick(() => scroller.value?.scrollTo({ top: scroller.value.scrollHeight, behavior: 'smooth' })),
  { deep: true, immediate: true }
)
</script>

<template>
  <div ref="scroller" class="flex flex-col overflow-y-auto overscroll-contain">
    <ol class="mt-auto flex flex-col gap-4 p-4 sm:p-5" aria-live="polite">
      <li v-for="message in chat" :key="message.id" class="chat-in flex">
        <p
          v-if="message.role === 'user'"
          class="ml-auto max-w-[80%] rounded-[20px_6px_20px_20px] bg-brand px-4 py-2.5 text-[0.95rem] whitespace-pre-line text-brand-contrast"
        >
          {{ message.text }}
        </p>

        <div v-else class="flex w-full max-w-[92%] gap-3">
          <BrandMark class="mt-0.5 h-8 w-8 shrink-0" />
          <div class="flex min-w-0 flex-1 flex-col gap-3">
            <p
              class="flex w-fit items-center gap-3 rounded-[6px_20px_20px_20px] px-4 py-2.5 text-[0.95rem]"
              :class="message.kind === 'error' ? 'bg-danger-soft text-danger' : 'border border-line bg-surface'"
              :aria-busy="message.kind === 'working'"
            >
              {{ agentText(message) }}
              <span v-if="message.kind === 'working'" class="typing-dots flex gap-1" aria-hidden="true">
                <span />
                <span />
                <span />
              </span>
            </p>

            <ChatSlotChoices
              v-if="choiceSlot(message)"
              :ask="choiceSlot(message)!"
              :locale="locale"
              :messages="messages"
              :default-start="defaultStart"
              :default-end="defaultEnd"
              @pick="emit('pick', $event)"
            />

            <button
              v-if="showsNoExtra(message)"
              type="button"
              class="prompt-chip w-fit"
              @click="emit('pick', messages.chat.noExtra)"
            >
              {{ messages.chat.noExtra }}
            </button>

            <ChatPlanCard
              v-if="message.kind === 'plan'"
              :proposal="message.proposal"
              :locale="locale"
              :labels="messages.chat"
              compact
            />

            <button
              v-if="message.kind === 'ready' && canGenerate"
              type="button"
              class="btn-primary w-fit px-5 py-2.5 text-sm"
              @click="emit('generate')"
            >
              {{ messages.chat.generatePlan }}
            </button>

            <button
              v-if="message.kind === 'error'"
              type="button"
              class="btn-secondary w-fit px-4 py-2 text-sm"
              @click="emit('retry')"
            >
              <i class="pi pi-refresh text-xs" aria-hidden="true" />
              {{ messages.retry }}
            </button>
          </div>
        </div>
      </li>

      <li v-if="typing" class="flex items-center gap-3" :aria-label="messages.chat.agentName">
        <BrandMark class="h-8 w-8 shrink-0" />
        <span class="typing-dots flex gap-1 rounded-full border border-line bg-surface px-4 py-3" aria-hidden="true">
          <span />
          <span />
          <span />
        </span>
      </li>
    </ol>
  </div>
</template>
