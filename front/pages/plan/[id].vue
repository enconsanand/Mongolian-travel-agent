<script setup lang="ts">
import PlanDayCard from '~/components/TripPlan/PlanDayCard.vue'
import PlanOverview from '~/components/TripPlan/PlanOverview.vue'
import PlanProgram from '~/components/TripPlan/PlanProgram.vue'
import PlannerHeader from '~/components/TripPlanner/PlannerHeader.vue'
import { PLAN_MESSAGES } from '~/constants/tripPlan'
import type { StayChoice } from '~/types/trip-plan'

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
} = useTripPlan(String(route.params.id))
const auth = useCookieAuth()
const messages = computed(() => PLAN_MESSAGES[locale.value])
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
  if (error.value === 'planner_unavailable') return messages.value.plannerDown
  if (error.value === 'no_stays') return messages.value.nothingToBook
  return messages.value.genericError
})

async function submitChange() {
  if (await revise(change.value)) change.value = ''
}

onMounted(load)
useHead(() => ({ title: messages.value.title, htmlAttrs: { lang: locale.value } }))
</script>

<template>
  <div>
    <PlannerHeader
      :locale="locale"
      :language-group-label="locale === 'mn' ? 'Хэл' : 'Language'"
      @set-locale="locale = $event"
    />

    <main class="mx-auto min-h-screen w-full max-w-6xl px-4 pt-8 pb-40 sm:px-8">
      <p v-if="loading && !proposal" class="text-ink-muted">{{ messages.loading }}</p>

      <section v-else-if="!proposal" class="panel p-6 text-center">
        <p class="text-ink-muted">{{ messages.notFound }}</p>
        <NuxtLink to="/" class="btn-primary mt-4 px-5 py-2.5">
          {{ messages.backToPlanner }}
        </NuxtLink>
      </section>

      <template v-else>
        <div class="flex items-baseline justify-between gap-3">
          <h1 class="text-2xl font-semibold sm:text-3xl">{{ messages.title }}</h1>
          <span class="shrink-0 text-xs text-ink-subtle">{{ messages.version }} {{ proposal.version }}</span>
        </div>

        <p class="mt-3 text-sm leading-relaxed text-slate-400">{{ messages.draft }}</p>

        <div class="mt-5">
          <PlanOverview :proposal="proposal" :locale="locale" :messages="messages" />
        </div>

        <p
          v-if="staysChanged"
          class="mt-4 rounded-control border border-accent/50 bg-warning-soft p-3 text-sm text-warning"
          role="alert"
        >
          {{ messages.staysChanged }}
        </p>

        <div class="mt-6 lg:grid lg:grid-cols-[minmax(0,1fr)_20rem] lg:items-start lg:gap-6">
          <ol class="relative ml-3 space-y-4 border-l border-emerald-400/40 pl-6 lg:col-start-1">
            <PlanDayCard
              v-for="(day, index) in proposal.days"
              :key="day.day"
              :day="day"
              :catalog="proposal.catalog"
              :locale="locale"
              :messages="messages"
              :has-night="index < proposal.days.length - 1"
              :night-bounds="day.stay ? nightBounds(day.to_place_id) : null"
              :choices-open="openDay === day.day"
              :stay-choices="openDay === day.day ? stayChoices : null"
              @adjust="moveNights(day.to_place_id, $event)"
              @toggle-stays="toggleStays(day.day, day.to_place_id)"
              @pick-stay="pickStay(day.to_place_id, $event)"
            />
          </ol>

          <aside
            v-if="program.length"
            class="mt-6 lg:sticky lg:top-24 lg:col-start-2 lg:row-span-2 lg:row-start-1 lg:mt-0"
          >
            <PlanProgram :events="program" :locale="locale" :messages="messages" />
          </aside>

          <form class="panel mt-6 p-5 lg:col-start-1" @submit.prevent="submitChange">
            <label for="plan-change" class="text-sm font-semibold">{{ messages.reviseLabel }}</label>
            <p class="mt-1 text-xs leading-relaxed text-ink-muted">{{ messages.reviseHint }}</p>
            <p v-if="proposal.changes.length" class="mt-1 text-xs text-ink-muted">
              {{ messages.changesSoFar }}: {{ proposal.changes.join(' · ') }}
            </p>
            <textarea
              id="plan-change"
              v-model="change"
              rows="2"
              maxlength="500"
              class="planner-field mt-3 text-sm"
              :placeholder="messages.revisePlaceholder"
            />
            <button
              type="submit"
              class="btn-secondary mt-3 w-full py-2.5 text-sm disabled:opacity-50"
              :disabled="!change.trim() || busy !== null"
            >
              <i :class="busy === 'revise' ? 'pi pi-spinner pi-spin' : 'pi pi-refresh'" aria-hidden="true" />
              {{ busy === 'revise' ? messages.revising : messages.revise }}
            </button>
          </form>
        </div>
      </template>
    </main>

    <div v-if="proposal" class="sticky bottom-0 z-30 border-t border-line bg-surface">
      <div class="mx-auto max-w-6xl px-4 py-3 sm:px-8">
        <p v-if="errorMessage" class="mb-2 text-center text-sm text-danger" role="alert">{{ errorMessage }}</p>
        <button
          type="button"
          class="btn-primary w-full py-3.5 text-sm disabled:opacity-50 sm:text-base"
          :disabled="!canBook || busy !== null"
          @click="accept"
        >
          <i :class="busy === 'accept' ? 'pi pi-spinner pi-spin' : 'pi pi-check'" aria-hidden="true" />
          {{ busy === 'accept' ? messages.booking : messages.book }}
        </button>
        <p v-if="proposal.days.some((day) => day.event_ids.length)" class="mb-1.5 text-center text-xs text-ink-muted">
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
</template>
