<script setup lang="ts">
import { formatTripRange } from '~/utils/tripFacts'
import { addDays } from '~/utils/dates'
import { formatMonthDay } from '~/utils/tripPlan'
import type { AppLocale } from '~/types/trip-planner'

interface Photo {
  url: string
  author: string
  license: string
  source: string
}
interface Program {
  id: string
  name: string
  description?: string
  place_id: string
  aimag: string
  start_date: string
  end_date: string
  cover_image_url?: string | null
  images?: Photo[]
}

const { locale, draft } = defineProps<{
  locale: AppLocale
  /** The request field, so a chosen program can show as already added */
  draft: string
}>()

const emit = defineEmits<{
  choose: [text: string]
}>()

const api = useApi()
const year = new Date().getFullYear()
const programs = ref<Program[]>([])
const places = ref<Record<string, string>>({})
const failed = ref(false)

const copy = computed(() =>
  locale === 'mn'
    ? {
        eyebrow: `${year} оны эвент`,
        title: 'Удахгүй болох эвентүүд',
        empty: 'Энэ онд эвент алга.',
        failed: 'Эвент ачаалж чадсангүй.',
        choose: 'Эвентэд оролцонгоо аялах',
        added: 'Талбарт нэмсэн',
      }
    : {
        eyebrow: `${year} events`,
        title: 'Coming events',
        empty: 'No events this year.',
        failed: 'Could not load events.',
        choose: 'Travel while joining the event',
        added: 'Added to the field',
      }
)

function dayCount(start: string, end: string) {
  const a = new Date(`${start}T00:00:00`).getTime()
  const b = new Date(`${end}T00:00:00`).getTime()
  return Math.round((b - a) / 86_400_000) + 1
}

/** A long festival becomes a short stay the traveller can edit in the field. */
function stayEnd(start: string, end: string) {
  if (dayCount(start, end) <= 7) return end
  const capped = addDays(start, 3)
  return capped < end ? capped : end
}

function placeName(program: Program) {
  return places.value[program.place_id] || program.aimag
}

function requestLine(program: Program) {
  const place = placeName(program)
  const range = formatTripRange(program.start_date, stayEnd(program.start_date, program.end_date), locale)
  return locale === 'mn'
    ? `${place}-д хононо. ${range}. ${program.name}.`
    : `Stay in ${place}. ${range}. ${program.name}.`
}

function chosen(program: Program) {
  return draft.includes(program.name)
}

async function load() {
  failed.value = false
  const headers = { 'Accept-Language': locale }
  const [eventRes, placeRes] = await Promise.all([
    api.get<Program[]>(`/events?date_from=${year}-01-01&date_to=${year}-12-31&limit=200`, { headers }),
    api.get<{ id: string; name: string }[]>('/places?limit=500', { headers }),
  ])
  if (!eventRes.data) {
    failed.value = true
    programs.value = []
    return
  }
  programs.value = [...eventRes.data].sort((a, b) => a.start_date.localeCompare(b.start_date))
  places.value = Object.fromEntries((placeRes.data ?? []).map((place) => [place.id, place.name]))
}

watch(() => locale, load)
onMounted(load)
</script>

<template>
  <section id="events">
    <p class="text-xs font-semibold tracking-[0.22em] text-accent-ink uppercase">{{ copy.eyebrow }}</p>
    <h2 class="mt-1 font-display text-2xl font-bold text-ink">{{ copy.title }}</h2>
    <p v-if="failed" class="mt-4 text-sm text-danger">{{ copy.failed }}</p>
    <p v-else-if="!programs.length" class="mt-4 text-sm text-ink-muted">{{ copy.empty }}</p>
    <ul v-else class="mt-4 flex snap-x gap-4 overflow-x-auto pb-3">
      <li
        v-for="program in programs"
        :key="program.id"
        class="flex w-72 shrink-0 snap-start flex-col overflow-hidden rounded-card border bg-surface"
        :class="chosen(program) ? 'border-accent' : 'border-line'"
      >
        <img
          v-if="program.cover_image_url"
          :src="program.cover_image_url"
          :alt="program.name"
          class="h-28 w-full object-cover"
          loading="lazy"
        />
        <div class="flex flex-1 flex-col p-4">
          <p class="text-xs font-semibold tracking-wide text-accent-ink uppercase">
            {{ formatMonthDay(program.start_date, locale) }} – {{ formatMonthDay(program.end_date, locale) }}
          </p>
          <h3 class="mt-1 font-display text-lg font-bold">{{ program.name }}</h3>
          <p class="mt-0.5 text-sm text-ink-muted">{{ placeName(program) }}</p>
          <p v-if="program.description" class="mt-2 line-clamp-3 flex-1 text-sm leading-relaxed text-ink">
            {{ program.description }}
          </p>
          <p v-if="program.images?.[0]" class="mt-2 truncate text-[10px] text-ink-subtle">
            <a :href="program.images[0].source" class="hover:underline" target="_blank" rel="noopener noreferrer">
              {{ program.images[0].author }} · {{ program.images[0].license }}
            </a>
          </p>
          <button
            type="button"
            class="btn-primary mt-4 w-full px-3 py-2.5 text-sm"
            @click="emit('choose', requestLine(program))"
          >
            {{ chosen(program) ? copy.added : copy.choose }}
          </button>
        </div>
      </li>
    </ul>
  </section>
</template>
