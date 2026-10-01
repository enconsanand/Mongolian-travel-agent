<script setup lang="ts">
import BrandMark from '~/components/Common/BrandMark.vue'
import ChatPlanCard from '~/components/TripPlanner/ChatPlanCard.vue'
import type { AppLocale, TripPlannerMessages } from '~/types/trip-planner'
import type { ChatMessage } from '~/composables/useTripPlanner'

/** The conversation with the agent, in a box of fixed height that keeps its newest message in view */
const { chat, locale, messages, typing } = defineProps<{
  chat: ChatMessage[]
  locale: AppLocale
  messages: TripPlannerMessages
  /** The agent is about to answer: show its typing dots */
  typing: boolean
}>()

const emit = defineEmits<{ retry: [] }>()

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
              class="w-fit rounded-[6px_20px_20px_20px] px-4 py-2.5 text-[0.95rem]"
              :class="message.kind === 'error' ? 'bg-danger-soft text-danger' : 'border border-line bg-surface'"
            >
              {{ message.text }}
            </p>

            <ul v-if="message.kind === 'working'" class="space-y-2 pl-1 text-sm">
              <li
                v-for="step in message.steps"
                :key="step.id"
                class="flex items-center gap-2.5"
                :class="
                  step.status === 'complete'
                    ? 'text-success'
                    : step.status === 'active'
                      ? 'font-medium text-ink'
                      : 'text-ink-subtle'
                "
              >
                <i
                  :class="
                    step.status === 'complete'
                      ? 'pi pi-check-circle'
                      : step.status === 'active'
                        ? 'pi pi-spinner pi-spin'
                        : 'pi pi-circle'
                  "
                  aria-hidden="true"
                />
                {{ step.label }}
              </li>
            </ul>

            <ChatPlanCard
              v-else-if="message.kind === 'plan'"
              :proposal="message.proposal"
              :locale="locale"
              :labels="messages.chat"
              compact
            />

            <button
              v-else-if="message.kind === 'error'"
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
