<script setup lang="ts">
import PhotoStrip from '~/components/TripPlan/PhotoStrip.vue'
import { STAY_TYPE_LABELS, type PlanMessages } from '~/constants/tripPlan'
import { UNIT_LABELS } from '~/constants/checkout'
import type { PlanDay, Proposal, StayChoice, ImageCredit } from '~/types/trip-plan'
import type { AppLocale } from '~/types/trip-planner'
import { formatDayDate, formatDriveTime, formatMnt } from '~/utils/tripPlan'

const {
  day,
  catalog,
  locale,
  messages,
  nightBounds = null,
  stayChoices = null,
  choicesOpen = false,
  drive = null,
} = defineProps<{
  day: PlanDay
  catalog: Proposal['catalog']
  locale: AppLocale
  messages: PlanMessages
  /** The day has a night (every day but the last) */
  hasNight: boolean
  /** Set on the first night of a stop, so the traveller can move nights and swap the stay */
  nightBounds?: { down: boolean; up: boolean } | null
  stayChoices?: StayChoice[] | null
  choicesOpen?: boolean
  /** Google's driving distance and time for the day, when the map has the real route */
  drive?: { km: number; min: number } | null
}>()

const emit = defineEmits<{
  adjust: [delta: number]
  toggleStays: []
  pickStay: [stayId: string]
}>()

const placeName = (id: string) => catalog.places[id]?.name ?? id
const isFreeDay = computed(() => day.from_place_id === day.to_place_id && day.via_place_ids.length === 0)
const stayId = computed(() => day.stay?.stay_id ?? day.stay_id)
const stay = computed(() => (stayId.value ? catalog.stays[stayId.value] : undefined))
const photos = computed(() => (stay.value?.images?.length ? stay.value.images : []))
const credit = computed(() => photos.value[0])
const reviews = computed(() => stay.value?.reviews ?? [])
const dateLabel = computed(() => formatDayDate(day.date, locale))
const gallery = ref<ImageCredit[]>([])
const photoIndex = ref(0)
const openPhoto = computed(() => gallery.value[photoIndex.value] ?? null)

function showPhoto(photo: ImageCredit, photos: ImageCredit[] = []) {
  const list = photos.length ? photos : [photo]
  gallery.value = list
  const index = list.findIndex((item) => item.url === photo.url)
  photoIndex.value = index < 0 ? 0 : index
}

function stepPhoto(delta: number) {
  const next = photoIndex.value + delta
  if (next < 0 || next >= gallery.value.length) return
  photoIndex.value = next
}

function onKey(event: KeyboardEvent) {
  if (!openPhoto.value) return
  if (event.key === 'Escape') gallery.value = []
  if (event.key === 'ArrowRight') stepPhoto(1)
  if (event.key === 'ArrowLeft') stepPhoto(-1)
}

onMounted(() => window.addEventListener('keydown', onKey))
onUnmounted(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <li class="panel relative p-4 sm:p-5">
    <span
      class="absolute top-6 -left-[1.7rem] h-3 w-3 rounded-full border-2 border-brand bg-surface"
      aria-hidden="true"
    />
    <div class="flex items-baseline justify-between gap-3">
      <p class="text-xs font-semibold tracking-wide text-accent-ink uppercase">
        {{ locale === 'mn' ? `${day.day}-р ${messages.day}` : `${messages.day} ${day.day}` }} · {{ dateLabel }}
      </p>
      <p v-if="drive || day.distance_km" class="shrink-0 text-xs text-ink-muted">
        <i class="pi pi-car mr-1" aria-hidden="true" />
        {{ drive?.km ?? day.distance_km }} {{ locale === 'mn' ? 'км' : 'km' }} ·
        {{ formatDriveTime(drive?.min ?? day.drive_time_min, locale) }}
      </p>
    </div>

    <h3 class="mt-1 text-base font-semibold sm:text-lg">
      <template v-if="isFreeDay">{{ messages.freeDay }} · {{ placeName(day.to_place_id) }}</template>
      <template v-else>{{ placeName(day.from_place_id) }} → {{ placeName(day.to_place_id) }}</template>
    </h3>
    <p v-if="day.via_place_ids.length" class="mt-1 text-sm text-ink-muted">
      <i class="pi pi-map-marker mr-1" aria-hidden="true" />
      {{ messages.via }}:
      {{ day.via_place_ids.map(placeName).join(', ') }}
    </p>
    <p v-if="day.note" class="mt-2 text-sm leading-relaxed text-ink-muted">{{ day.note }}</p>

    <p v-if="stay && !day.stay" class="mt-3 text-sm text-ink-muted">{{ messages.sameStay }} · {{ stay.name }}</p>
    <div v-else-if="stay" class="mt-4 min-w-0 overflow-hidden rounded-control bg-surface-muted p-3">
      <div class="flex gap-3">
        <figure class="w-28 shrink-0 sm:w-40">
          <button
            v-if="photos[0]"
            type="button"
            class="block w-full cursor-zoom-in"
            :aria-label="messages.enlargePhoto"
            @click="showPhoto(photos[0], photos)"
          >
            <img
              :src="photos[0].url"
              :alt="stay.name"
              class="aspect-4/3 w-full rounded-inner object-cover"
              loading="lazy"
            />
          </button>
          <img
            v-else
            :src="stay.cover_image_url"
            :alt="stay.name"
            class="aspect-4/3 w-full rounded-inner object-cover"
            loading="lazy"
          />
          <figcaption v-if="credit" class="mt-1 truncate text-[10px] text-ink-subtle">
            <a :href="credit.source" target="_blank" rel="noopener" class="hover:underline">
              {{ messages.photo }}: {{ credit.author }}, {{ credit.license }}
            </a>
          </figcaption>
        </figure>
        <div class="min-w-0 text-sm">
          <p class="text-xs text-ink-muted">{{ messages.stay }} · {{ STAY_TYPE_LABELS[stay.type]?.[locale] }}</p>
          <p class="font-semibold">{{ stay.name }}</p>
          <p class="text-xs text-accent-ink">
            <i class="pi pi-star-fill mr-1" aria-hidden="true" />
            {{ stay.rating }} ({{ stay.reviews_count }})
          </p>
          <template v-if="day.stay">
            <p class="mt-1 text-xs text-ink-muted">
              {{ day.stay.units }} {{ messages.units }}
              {{ UNIT_LABELS[day.stay.unit_type]?.[locale] ?? day.stay.unit_type }} · {{ day.stay.nights }}
              {{ messages.nights }}
            </p>
            <p class="mt-1 font-semibold text-brand">{{ formatMnt(day.stay.total_mnt, locale) }}</p>
          </template>
        </div>
      </div>
      <PhotoStrip
        v-if="photos.length > 1"
        class="mt-3"
        :photos="photos"
        :alt="stay.name"
        :enlarge-label="messages.enlargePhoto"
        @open="showPhoto($event, photos)"
      />
      <ul v-if="reviews.length" class="mt-3 space-y-2">
        <li v-for="review in reviews" :key="review.author + review.text" class="rounded-control bg-surface p-2 text-sm">
          <p class="text-xs text-accent-ink">★ {{ review.rating }} · {{ review.author }}</p>
          <p class="mt-1 leading-relaxed">{{ review.text }}</p>
        </li>
      </ul>
      <div v-if="nightBounds" class="mt-3 flex flex-wrap items-center gap-2">
        <button
          type="button"
          class="flex h-8 w-8 items-center justify-center rounded-full border border-line disabled:opacity-30"
          :disabled="!nightBounds.down"
          :aria-label="`${placeName(day.to_place_id)} −`"
          @click="emit('adjust', -1)"
        >
          −
        </button>
        <span class="text-xs text-ink-muted">{{ day.stay?.nights }} {{ messages.nights }}</span>
        <button
          type="button"
          class="flex h-8 w-8 items-center justify-center rounded-full border border-line disabled:opacity-30"
          :disabled="!nightBounds.up"
          :aria-label="`${placeName(day.to_place_id)} +`"
          @click="emit('adjust', 1)"
        >
          +
        </button>
        <button
          type="button"
          class="rounded-full border border-brand px-3 py-1 text-xs font-semibold text-brand"
          @click="emit('toggleStays')"
        >
          {{ choicesOpen ? messages.hideStays : messages.changeStay }}
        </button>
      </div>
      <p v-if="(day.stay?.nights ?? 0) > 1" class="mt-2 text-xs leading-relaxed text-ink-muted">
        {{
          messages.onePlaceOneStay
            .replace('{place}', placeName(day.to_place_id))
            .replace('{nights}', String(day.stay?.nights))
        }}
      </p>
    </div>
    <p v-if="choicesOpen && (day.stay?.nights ?? 0) > 1" class="mt-3 text-xs leading-relaxed text-ink-muted">
      {{ messages.oneStayForNights.replace('{nights}', String(day.stay?.nights)) }}
    </p>
    <ul v-if="choicesOpen && stayChoices?.length" class="mt-3 min-w-0 space-y-3">
      <li
        v-for="choice in stayChoices"
        :key="choice.id"
        class="min-w-0 cursor-pointer overflow-hidden rounded-control border p-3 transition-colors"
        :class="choice.selected ? 'border-brand bg-brand-soft' : 'border-line bg-surface'"
        @click="emit('pickStay', choice.id)"
      >
        <div class="flex gap-3">
          <button
            v-if="choice.images?.[0]"
            type="button"
            class="h-20 w-28 shrink-0 cursor-zoom-in"
            :aria-label="messages.enlargePhoto"
            @click.stop="showPhoto(choice.images[0], choice.images ?? [])"
          >
            <img
              :src="choice.images[0].url"
              :alt="choice.name"
              class="h-full w-full rounded-inner object-cover"
              loading="lazy"
            />
          </button>
          <img
            v-else-if="choice.cover_image_url"
            :src="choice.cover_image_url"
            :alt="choice.name"
            class="h-20 w-28 shrink-0 rounded-inner object-cover"
          />
          <button
            type="button"
            class="min-w-0 flex-1 text-left text-sm"
            :aria-pressed="choice.selected"
            @click.stop="emit('pickStay', choice.id)"
          >
            <span class="block font-semibold">{{ choice.name }}</span>
            <span class="text-xs text-accent-ink">★ {{ choice.rating }} ({{ choice.reviews_count }})</span>
            <span class="mt-1 block font-semibold text-brand">{{ formatMnt(choice.total_mnt, locale) }}</span>
            <span class="mt-1 block text-xs text-ink-muted">
              <template v-if="choice.meals">{{ messages.mealsIncluded }}</template>
              <template v-if="choice.km > 1">
                <template v-if="choice.meals">·</template>
                {{ messages.kmAway.replace('{km}', String(choice.km)) }}
              </template>
            </span>
          </button>
        </div>
        <PhotoStrip
          v-if="(choice.images?.length ?? 0) > 1"
          class="mt-2"
          :photos="choice.images ?? []"
          :alt="choice.name"
          :enlarge-label="messages.enlargePhoto"
          thumb-class="h-16 w-24"
          @open="showPhoto($event, choice.images ?? [])"
        />
        <p
          v-for="review in choice.reviews ?? []"
          :key="review.author + review.text"
          class="mt-2 text-xs leading-relaxed text-ink-muted"
        >
          <span class="text-accent-ink">★ {{ review.rating }} {{ review.author }}.</span>
          {{ review.text }}
        </p>
      </li>
    </ul>

    <Teleport to="body">
      <div
        v-if="openPhoto"
        class="fixed inset-0 z-[80] flex items-center justify-center bg-black/80 p-4"
        role="dialog"
        aria-modal="true"
        @click="gallery = []"
      >
        <div class="flex max-w-5xl items-center gap-2" @click.stop>
          <button
            v-if="gallery.length > 1"
            type="button"
            class="grid h-11 w-11 shrink-0 place-items-center rounded-full border border-white/40 text-white disabled:opacity-30"
            :disabled="photoIndex === 0"
            :aria-label="messages.prevPhoto"
            @click="stepPhoto(-1)"
          >
            <i class="pi pi-chevron-left" aria-hidden="true" />
          </button>
          <figure class="min-w-0 flex-1">
            <img :src="openPhoto.url" :alt="stay?.name" class="max-h-[80vh] w-full object-contain" />
            <figcaption class="mt-2 flex items-center justify-between gap-3 text-xs text-white">
              <a :href="openPhoto.source" target="_blank" rel="noopener" class="truncate hover:underline">
                {{ messages.photo }}: {{ openPhoto.author }}, {{ openPhoto.license }}
              </a>
              <button
                type="button"
                class="shrink-0 rounded-full border border-white/40 px-3 py-1"
                @click="gallery = []"
              >
                {{ messages.closePhoto }}
              </button>
            </figcaption>
          </figure>
          <button
            v-if="gallery.length > 1"
            type="button"
            class="grid h-11 w-11 shrink-0 place-items-center rounded-full border border-white/40 text-white disabled:opacity-30"
            :disabled="photoIndex >= gallery.length - 1"
            :aria-label="messages.nextPhoto"
            @click="stepPhoto(1)"
          >
            <i class="pi pi-chevron-right" aria-hidden="true" />
          </button>
        </div>
      </div>
    </Teleport>
  </li>
</template>
