<script setup lang="ts">
import PlanChat, { type PlanChatEntry } from '~/components/TripPlan/PlanChat.vue'
import PlanDayCard from '~/components/TripPlan/PlanDayCard.vue'
import PlanOverview from '~/components/TripPlan/PlanOverview.vue'
import PlanProgram from '~/components/TripPlan/PlanProgram.vue'
import PlannerHeader from '~/components/TripPlanner/PlannerHeader.vue'
import TripRouteMap from '~/components/TripPlanner/TripRouteMap.vue'
import { PLAN_MESSAGES } from '~/constants/tripPlan'
import type { ExtraStop, StayChoice } from '~/types/trip-plan'
import type { StopLegs } from '~/utils/drivingRoute'

definePageMeta({ layout: 'planner', auth: false })

const route = useRoute()
const {
  locale,
  proposal,
  loading,
  busy,
  error,
  staysChanged,
  tripFits,
  canBook,
  load,
  revise,
  editNights,
  loadStayChoices,
  chooseStay,
  accept,
  save,
} = useTripPlan(String(route.params.id))
const auth = useCookieAuth()
const { messages: accountMessages } = useAccountMessages()
const messages = computed(() => PLAN_MESSAGES[locale.value])
/** Summary and day notes in the page language (Orchu translates a plan written in the other one) */
const { shown, translating, failed: translationFailed, isTranslated } = usePlanTranslation(proposal, locale)
/** tsuurAI reads the plan aloud; it speaks Mongolian only */
const { speaking, loading: speechLoading, error: speechError, toggle: toggleSpeech, stop: stopSpeech } = useSpeech()
const listenTexts = computed(() => {
  const plan = shown.value
  return plan ? [plan.summary, ...plan.days.map((day) => day.note ?? '')] : []
})
watch(locale, stopSpeech)
const change = ref('')
/** The day whose stay list is open. Keyed by day, so one click does not open the list under every night at that place. */
const openDay = ref<number | null>(null)
const stayChoices = ref<StayChoice[]>([])
const staysLoading = ref(false)

const nightBlocks = computed(() => {
  const days = proposal.value?.days ?? []
  const blocks: { placeId: string; nights: number }[] = []
  for (const day of days.slice(0, -1)) {
    const last = blocks.at(-1)
    if (last && day.from_place_id === day.to_place_id && day.to_place_id === last.placeId) last.nights += 1
    else blocks.push({ placeId: day.to_place_id, nights: 1 })
  }
  return blocks
})

const program = computed(() => {
  const catalog = proposal.value?.catalog.events ?? {}
  const seen = new Set<string>()
  const items = []
  for (const day of proposal.value?.days ?? []) {
    for (const id of day.event_ids) {
      const event = catalog[id]
      if (!event || seen.has(id)) continue
      seen.add(id)
      items.push({ id, ...event })
    }
  }
  return items
})

function nightBounds(placeId: string) {
  const blocks = nightBlocks.value
  const index = blocks.findIndex((block) => block.placeId === placeId)
  if (index < 0 || blocks.length < 2) return { down: false, up: false }
  const other = index === blocks.length - 1 ? index - 1 : blocks.length - 1
  return { down: blocks[index]!.nights > 1, up: blocks[other]!.nights > 1 }
}

function currentStayId(placeId: string) {
  return proposal.value?.days.find((day) => day.to_place_id === placeId && day.stay)?.stay?.stay_id
}

async function toggleStays(day: number, placeId: string) {
  if (staysLoading.value) return
  if (openDay.value === day) {
    openDay.value = null
    return
  }
  staysLoading.value = true
  try {
    const current = currentStayId(placeId)
    stayChoices.value = (await loadStayChoices(placeId)).map((choice) => ({
      ...choice,
      selected: choice.id === current,
    }))
    openDay.value = day
  } finally {
    staysLoading.value = false
  }
}

async function moveNights(placeId: string, delta: number) {
  if (delta !== 1 && delta !== -1) return
  if (await editNights(placeId, delta)) stayChoices.value = []
}

let shownStay = 0

function showPickedStay(placeId: string, choice: StayChoice) {
  const current = proposal.value
  if (!current) return
  const priced = current.days.find((day) => day.to_place_id === placeId && day.stay)
  if (!priced?.stay) return
  const previous = current.catalog.stays[priced.stay.stay_id]
  const stays = current.totals.stays_mnt - priced.stay.total_mnt + choice.total_mnt
  const total = stays + current.totals.events_mnt
  proposal.value = {
    ...current,
    days: current.days.map((day) => {
      if (day.to_place_id !== placeId) return day
      if (day.stay) {
        return { ...day, stay_id: choice.id, stay: { ...day.stay, stay_id: choice.id, total_mnt: choice.total_mnt } }
      }
      return day.stay_id ? { ...day, stay_id: choice.id } : day
    }),
    totals: {
      ...current.totals,
      stays_mnt: stays,
      total_mnt: total,
      within_budget: current.totals.budget_mnt == null || total <= current.totals.budget_mnt,
    },
    catalog: {
      ...current.catalog,
      stays: {
        ...current.catalog.stays,
        [choice.id]: {
          name: choice.name,
          type: choice.type,
          aimag: previous?.aimag ?? '',
          rating: choice.rating,
          reviews_count: choice.reviews_count,
          reviews: choice.reviews ?? [],
          cover_image_url: choice.cover_image_url || choice.images?.[0]?.url || '',
          images: choice.images ?? [],
          check_in: previous?.check_in ?? '',
          check_out: previous?.check_out ?? '',
        },
      },
    },
  }
}

async function paintFrame() {
  await new Promise<void>((resolve) => {
    requestAnimationFrame(() => requestAnimationFrame(() => resolve()))
  })
}

async function pickStay(placeId: string, stayId: string) {
  const picked = stayChoices.value.find((choice) => choice.id === stayId)
  if (!picked || picked.selected) return
  const ticket = ++shownStay
  stayChoices.value = stayChoices.value.map((choice) => ({ ...choice, selected: choice.id === stayId }))
  await nextTick()
  await paintFrame()
  await new Promise((resolve) => setTimeout(resolve, 160))
  if (ticket !== shownStay) return
  showPickedStay(placeId, picked)
  openDay.value = null
  const saved = await chooseStay(placeId, stayId)
  if (ticket !== shownStay) return
  if (!saved) await load()
}

const errorMessage = computed(() => {
  if (!error.value || error.value === 'proposal_not_found') return null
  if (error.value === 'trip_locked') return accountMessages.value.trip_locked
  if (error.value === 'planner_unavailable') return messages.value.plannerDown
  if (error.value === 'no_stays') return messages.value.nothingToBook
  return messages.value.genericError
})

// Google's driving time and distance per day, once the map has the real route; until then the planner's estimate
const legs = ref<StopLegs>({})
const dayDrives = computed(() =>
  (proposal.value?.days ?? []).map((day) => {
    const path = [day.from_place_id, ...day.via_place_ids, day.to_place_id].filter((id, i, all) => all[i - 1] !== id)
    const parts = path.slice(1).map((to, i) => legs.value[`${path[i]}>${to}`])
    if (path.length < 2 || parts.some((leg) => !leg)) return null
    return {
      km: Math.round(parts.reduce((sum, leg) => sum + leg!.distanceM, 0) / 1000),
      min: Math.round(parts.reduce((sum, leg) => sum + leg!.durationSec, 0) / 60),
    }
  })
)

// Stops added on the map: the route goes through them at once, and the agent is asked to replan around them
const extraStops = ref<ExtraStop[]>([])
async function addStop(stop: ExtraStop) {
  if (busy.value !== null || extraStops.value.some((extra) => extra.id === stop.id)) return
  extraStops.value.push(stop)
  const revised = await ask(
    locale.value === 'mn' ? `${stop.name}-г маршрутад нэмээрэй` : `Add ${stop.name} to the route`
  )
  // The plan did not change, so the map should not keep a stop the plan does not have
  if (!revised) extraStops.value = extraStops.value.filter((extra) => extra.id !== stop.id)
}

// The chat under the plan: every message revises this plan in place, so the page never changes
const chatLog = ref<PlanChatEntry[]>([])
let nextEntryId = 0

/** The new route in one line, e.g. "Уран Тогоо 1 → Хөвсгөл нуур 3", so the reply says what actually changed */
function routeLine() {
  const places = proposal.value?.catalog.places ?? {}
  return nightBlocks.value
    .map((block) => `${places[block.placeId]?.name ?? block.placeId} ${block.nights} ${messages.value.nights}`)
    .join(' → ')
}

/** One chat message: revise the plan with it and answer in the chat. ``typed`` when it came from the chat bar. */
async function ask(text: string, typed = false): Promise<boolean> {
  if (busy.value !== null) return false
  chatLog.value.push({ id: nextEntryId++, role: 'user', text })
  if (typed) change.value = ''
  const revised = await revise(text)
  const plan = proposal.value
  chatLog.value.push(
    revised && plan
      ? {
          id: nextEntryId++,
          role: 'agent',
          text: `${messages.value.chatRevised} (${messages.value.version} ${plan.version}): ${routeLine()}`,
        }
      : { id: nextEntryId++, role: 'agent', text: errorMessage.value ?? messages.value.genericError, failed: true }
  )
  // Nothing was lost: what the traveller typed comes back so they can send it again
  if (!revised && typed && !change.value) change.value = text
  return revised
}

/** A failed revision already says so in the chat; the bar under it is for booking errors */
const barError = computed(() => (chatLog.value.at(-1)?.failed && busy.value === null ? null : errorMessage.value))

onMounted(async () => {
  await load()
  if (proposal.value && route.query.save === '1') await save()
})
useHead(() => ({ title: messages.value.title, htmlAttrs: { lang: locale.value } }))
</script>

<template>
  <div>
    <PlannerHeader
      :locale="locale"
      :language-group-label="locale === 'mn' ? 'Хэл' : 'Language'"
      @set-locale="locale = $event"
    />

    <p v-if="loading && !proposal" class="mx-auto max-w-3xl px-4 pt-8 text-ink-muted">{{ messages.loading }}</p>

    <section v-else-if="!proposal" class="panel mx-auto mt-8 max-w-3xl p-6 text-center">
      <p class="text-ink-muted">{{ messages.notFound }}</p>
      <NuxtLink to="/" class="btn-primary mt-4 px-5 py-2.5">
        {{ messages.backToPlanner }}
      </NuxtLink>
    </section>

    <!-- The map fills the screen on the left and stays put; the itinerary scrolls on the right -->
    <div v-else class="lg:grid lg:grid-cols-[minmax(0,1fr)_minmax(0,36rem)]">
      <div class="h-[45vh] lg:sticky lg:top-16 lg:h-[calc(100vh-4rem)]">
        <TripRouteMap
          class="h-full rounded-none! border-0! shadow-none!"
          :proposal="proposal"
          :locale="locale"
          :extra-stops="extraStops"
          @legs="legs = $event"
          @add-stop="addStop"
        />
      </div>

      <div class="flex min-w-0 flex-col lg:min-h-[calc(100vh-4rem)] lg:border-l lg:border-line">
        <main class="flex-1 px-4 pt-6 pb-8 sm:px-6">
          <div class="flex items-baseline justify-between gap-3">
            <h1 class="text-2xl font-semibold sm:text-3xl">{{ messages.title }}</h1>
            <div class="flex shrink-0 flex-col items-end gap-2">
              <span class="text-xs text-ink-subtle">{{ messages.version }} {{ proposal.version }}</span>
              <button class="btn-secondary px-3 py-2 text-xs disabled:opacity-60" :disabled="!!busy" @click="save">
                <i :class="busy === 'save' ? 'pi pi-spinner pi-spin' : 'pi pi-bookmark'" aria-hidden="true" />
                {{ accountMessages.save }}
              </button>
            </div>
          </div>

          <p class="mt-3 text-sm leading-relaxed text-ink-muted">{{ messages.draft }}</p>

          <div class="mt-5 flex flex-wrap items-center justify-end gap-3 text-xs text-ink-muted">
            <span v-if="translating">
              <i class="pi pi-spinner pi-spin mr-1" aria-hidden="true" />
              {{ messages.translating }}
            </span>
            <span v-else-if="translationFailed" class="text-warning">{{ messages.translationFailed }}</span>
            <span v-else-if="isTranslated">
              <i class="pi pi-language mr-1" aria-hidden="true" />
              {{ messages.translated }}
            </span>
            <button
              v-if="locale === 'mn'"
              type="button"
              class="btn-secondary px-3 py-2 text-xs"
              :aria-pressed="speaking"
              :aria-label="messages.listenLabel"
              :title="messages.listenLabel"
              :disabled="translating"
              @click="toggleSpeech(listenTexts)"
            >
              <i
                :class="speechLoading ? 'pi pi-spinner pi-spin' : speaking ? 'pi pi-stop' : 'pi pi-volume-up'"
                aria-hidden="true"
              />
              {{ speaking ? messages.stopListening : messages.listen }}
            </button>
          </div>
          <p v-if="speechError" class="mt-2 text-right text-xs text-danger" role="alert">
            {{ speechError === 'unavailable' ? messages.speechUnavailable : messages.speechFailed }}
          </p>

          <div class="mt-3">
            <PlanOverview :proposal="shown ?? proposal" :locale="locale" :messages="messages" />
          </div>

          <p
            v-if="staysChanged"
            class="mt-4 rounded-control border border-accent/50 bg-warning-soft p-3 text-sm text-warning"
            role="alert"
          >
            {{ messages.staysChanged }}
          </p>

          <ol class="relative mt-6 ml-3 space-y-4 border-l border-emerald-400/40 pl-6">
            <PlanDayCard
              v-for="(day, index) in (shown ?? proposal).days"
              :key="day.day"
              :day="day"
              :drive="dayDrives[index]"
              :catalog="proposal.catalog"
              :locale="locale"
              :messages="messages"
              :busy="busy === 'edit'"
              :has-night="index < proposal.days.length - 1"
              :night-bounds="day.stay ? nightBounds(day.to_place_id) : null"
              :choices-open="openDay === day.day"
              :stay-choices="openDay === day.day ? stayChoices : null"
              @adjust="moveNights(day.to_place_id, $event)"
              @toggle-stays="toggleStays(day.day, day.to_place_id)"
              @pick-stay="pickStay(day.to_place_id, $event)"
            />
          </ol>

          <aside v-if="program.length" class="mt-6">
            <PlanProgram :events="program" :locale="locale" :messages="messages" />
          </aside>
        </main>

        <!-- Chat and booking stay at the bottom of the itinerary; the plan above updates as the agent answers -->
        <div class="sticky bottom-0 z-30 border-t border-line bg-surface px-4 py-3 sm:px-6">
          <PlanChat
            v-model="change"
            :locale="locale"
            :entries="chatLog"
            :working="busy === 'revise'"
            :locked="busy !== null"
            :earlier-changes="proposal.changes"
            @send="ask($event, true)"
          />
          <p v-if="barError" class="mt-2 text-center text-sm text-danger" role="alert">{{ barError }}</p>
          <button
            type="button"
            class="btn-primary mt-3 w-full py-3 text-sm disabled:opacity-50 sm:text-base"
            :disabled="!canBook || busy !== null"
            @click="accept"
          >
            <i :class="busy === 'accept' ? 'pi pi-spinner pi-spin' : 'pi pi-check'" aria-hidden="true" />
            {{ busy === 'accept' ? messages.booking : messages.book }}
          </button>
          <p v-if="proposal.days.some((day) => day.event_ids.length)" class="mt-1.5 text-center text-xs text-ink-muted">
            {{ messages.eventsBookApart }}
          </p>
          <p class="mt-1.5 text-center text-xs text-ink-muted">
            {{
              !tripFits
                ? messages.tooShortToBook
                : !canBook
                  ? messages.nothingToBook
                  : auth.isAuthenticated.value
                    ? messages.bookHint
                    : messages.signInToBook
            }}
          </p>
        </div>
      </div>
    </div>
  </div>
</template>
