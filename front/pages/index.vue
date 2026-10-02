<script setup lang="ts">
import HeroShowcase from '~/components/TripPlanner/HeroShowcase.vue'
import ChatThread from '~/components/TripPlanner/ChatThread.vue'
import HomePrograms from '~/components/TripPlanner/HomePrograms.vue'
import PlannerHeader from '~/components/TripPlanner/PlannerHeader.vue'
import TripRouteMap from '~/components/TripPlanner/TripRouteMap.vue'
import TripRequestComposer from '~/components/TripPlanner/TripRequestComposer.vue'
import { BRAND } from '~/constants/brand'
import { HERO_SLIDES } from '~/constants/heroSlides'
import type { ExtraStop } from '~/types/trip-plan'
import type { AppLocale } from '~/types/trip-planner'

definePageMeta({
  layout: 'planner',
  auth: false,
})

const {
  locale,
  messages,
  draft,
  chat,
  busy,
  hasStarted,
  currentPlan,
  isListening,
  isTranscribing,
  voiceStatusLabel,
  voiceError,
  setLocale,
  toggleVoiceInput,
  canGenerate,
  pendingSlot,
  dateDefaults,
  send,
  pick,
  generate,
  retry,
  reset,
} = useTripPlanner()

const SLIDE_LABELS: Record<AppLocale, { group: string; previous: string; next: string; photo: string }> = {
  mn: { group: 'Зургийн цомог', previous: 'Өмнөх зураг', next: 'Дараах зураг', photo: 'Зураг' },
  en: { group: 'Photo gallery', previous: 'Previous photo', next: 'Next photo', photo: 'Photo' },
}
const SLIDE_INTERVAL_MS = 7000

const slideIndex = ref(0)
const slide = computed(() => HERO_SLIDES[slideIndex.value]!)
const pauseSlides = ref(false)

function showSlide(step: number) {
  slideIndex.value = (slideIndex.value + step + HERO_SLIDES.length) % HERO_SLIDES.length
}

const OR_PROGRAM: Record<AppLocale, string> = {
  mn: 'эвентүүд',
  en: 'or start from an event',
}

/** A chosen program is written into the request field. The same line is not added twice. */
function chooseProgram(line: string) {
  const current = draft.value.trim()
  if (!current.includes(line)) draft.value = current ? `${current} ${line}` : line
  nextTick(() => {
    document.getElementById('trip-composer')?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    document.getElementById('trip-request')?.focus()
  })
}

// Slides advance on their own unless the visitor is looking at one or prefers reduced motion
let slideTimer: ReturnType<typeof setInterval> | null = null
onMounted(() => {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
  slideTimer = setInterval(() => {
    if (!pauseSlides.value) showSlide(1)
  }, SLIDE_INTERVAL_MS)
})
onUnmounted(() => {
  if (slideTimer) clearInterval(slideTimer)
})

// Stops added on the map: the route goes through them at once, and the chat asks the agent to replan around them
const extraStops = ref<ExtraStop[]>([])
function addStop(stop: ExtraStop) {
  if (busy.value || extraStops.value.some((extra) => extra.id === stop.id)) return
  extraStops.value.push(stop)
  // Sent as its own message, so whatever the traveller is typing stays in the field
  pick(locale.value === 'mn' ? `${stop.name}-г маршрутад нэмээрэй` : `Add ${stop.name} to the route`)
}
watch(hasStarted, (started) => {
  if (!started) extraStops.value = []
})

/** The agent is about to ask its next question: show it typing */
const isAgentTyping = computed(() => busy.value && chat.value.at(-1)?.role === 'user')

const REQUEST_EXAMPLES: Record<AppLocale, string[]> = {
  mn: [
    '2 хүн 5 хоног Хөвсгөл нуур, морь унах',
    'Гэр бүлээрээ 3 хоног Тэрэлж, хэмнэлттэй',
    'Наадам үзэх 4 хоног, Хархорин',
  ],
  en: [
    '2 people, 5 days at Lake Khövsgöl, horse riding',
    'Family of 4, 3 days in Terelj, on a budget',
    '4 days for the Naadam and Kharkhorin',
  ],
}

useHead(() => ({
  title: messages.value.documentTitle,
  htmlAttrs: { lang: locale.value },
}))
</script>

<template>
  <div>
    <PlannerHeader :locale="locale" :language-group-label="messages.languageGroupLabel" @set-locale="setLocale" />

    <section class="relative overflow-hidden">
      <div
        :class="currentPlan ? 'lg:grid-cols-[1fr_1.15fr]' : 'lg:grid-cols-[1.3fr_1fr]'"
        class="mx-auto grid max-w-6xl grid-cols-1 items-center gap-10 px-4 pt-10 pb-20 sm:pt-14 lg:gap-12"
      >
        <div class="min-w-0">
          <p class="rise-in text-xs font-semibold tracking-[0.35em] text-accent-ink uppercase sm:text-sm">
            {{ BRAND.tagline[locale] }}
          </p>
          <template v-if="!hasStarted">
            <h1 class="rise-in mt-4 text-4xl leading-[1.05] font-semibold text-ink sm:text-5xl" style="--delay: 80ms">
              {{ messages.heroTitle }}
            </h1>
            <p class="rise-in mt-5 max-w-lg text-base text-ink-muted sm:text-lg" style="--delay: 160ms">
              {{ messages.heroSubtitle }}
            </p>
          </template>

          <!-- Once the conversation starts it takes the title's place, in a clear box above the bar -->
          <div v-else class="chat-in mt-4 flex h-[min(30rem,62vh)] flex-col rounded-card border border-line">
            <div class="flex items-center justify-between border-b border-line px-4 py-2.5">
              <span class="flex items-center gap-2 text-sm font-semibold">
                <span class="h-2 w-2 rounded-full bg-success" aria-hidden="true" />
                {{ messages.chat.agentName }}
              </span>
              <button
                type="button"
                class="flex items-center gap-1.5 rounded-full px-3 py-1 text-sm text-ink-muted transition-colors hover:bg-surface-muted hover:text-ink"
                @click="reset"
              >
                <i class="pi pi-plus text-xs" aria-hidden="true" />
                {{ messages.chat.newTrip }}
              </button>
            </div>
            <ChatThread
              class="min-h-0 flex-1"
              :chat="chat"
              :locale="locale"
              :messages="messages"
              :typing="isAgentTyping"
              :can-generate="canGenerate"
              :pending-slot="pendingSlot"
              :default-start="dateDefaults.start"
              :default-end="dateDefaults.end"
              @retry="retry"
              @generate="generate"
              @pick="pick"
            />
          </div>

          <TripRequestComposer
            id="trip-composer"
            v-model:trip-request="draft"
            class="rise-in"
            :class="hasStarted ? 'mt-3' : 'mt-8'"
            style="--delay: 240ms"
            :is-listening="isListening"
            :is-transcribing="isTranscribing"
            :voice-status-label="voiceStatusLabel"
            :request-label="messages.requestLabel"
            :request-placeholder="hasStarted ? messages.chat.replyPlaceholder : messages.requestPlaceholder"
            :voice-button-label="messages.voiceButtonLabel"
            :send-label="messages.generate"
            @toggle-voice="toggleVoiceInput"
            @submit="send"
          />
          <p v-if="voiceError" class="mt-2 px-7 text-sm text-danger" role="alert">{{ voiceError }}</p>
          <div v-if="!hasStarted" class="rise-in mt-4 flex flex-wrap gap-2" style="--delay: 320ms">
            <button
              v-for="example in REQUEST_EXAMPLES[locale]"
              :key="example"
              type="button"
              class="prompt-chip"
              @click="draft = example"
            >
              {{ example }}
            </button>
          </div>
        </div>

        <!-- Once there is a plan, its map takes the photo's place and follows every revision from the chat -->
        <TripRouteMap
          v-if="currentPlan"
          class="chat-in h-[min(36rem,72vh)]"
          :proposal="currentPlan"
          :locale="locale"
          :extra-stops="extraStops"
          @add-stop="addStop"
        />

        <div v-else class="min-w-0">
          <HeroShowcase
            class="rise-in"
            style="--delay: 120ms"
            :slide="slide"
            :alt="slide.title[locale]"
            :credit="`${SLIDE_LABELS[locale].photo}: ${slide.author} · ${slide.license}`"
            @mouseenter="pauseSlides = true"
            @mouseleave="pauseSlides = false"
          />
          <div
            class="rise-in panel mx-auto mt-4 flex max-w-md items-center gap-4 overflow-hidden p-0 pr-4"
            style="--delay: 320ms"
            role="group"
            :aria-label="SLIDE_LABELS[locale].group"
          >
            <img
              :src="slide.image"
              alt=""
              class="h-20 w-24 shrink-0 object-cover"
              :style="{ objectPosition: slide.focus }"
            />
            <p class="min-w-0 flex-1 truncate text-sm font-medium" aria-live="polite">{{ slide.title[locale] }}</p>
            <button
              type="button"
              class="grid h-9 w-9 shrink-0 place-items-center rounded-full border border-brand text-brand transition-colors hover:bg-brand-soft"
              :aria-label="SLIDE_LABELS[locale].previous"
              @click="showSlide(-1)"
            >
              <i class="pi pi-arrow-left text-sm" aria-hidden="true" />
            </button>
            <button
              type="button"
              class="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-brand text-brand-contrast transition-colors hover:bg-brand-hover"
              :aria-label="SLIDE_LABELS[locale].next"
              @click="showSlide(1)"
            >
              <i class="pi pi-arrow-right text-sm" aria-hidden="true" />
            </button>
          </div>
          <div class="mt-3 flex justify-center gap-1.5" aria-hidden="true">
            <span
              v-for="(item, index) in HERO_SLIDES"
              :key="item.id"
              class="h-1 rounded-full transition-[width,background-color] duration-300"
              :class="index === slideIndex ? 'w-6 bg-brand' : 'w-2 bg-line-strong'"
            />
          </div>
        </div>
      </div>
    </section>

    <div v-if="!hasStarted" class="mx-auto mt-4 max-w-6xl px-4 pb-16">
      <div class="mb-8 flex items-center gap-4 text-sm text-ink-muted">
        <span class="h-px flex-1 bg-line" />
        {{ OR_PROGRAM[locale] }}
        <span class="h-px flex-1 bg-line" />
      </div>
      <HomePrograms :locale="locale" :draft="draft" @choose="chooseProgram" />
    </div>
  </div>
</template>
