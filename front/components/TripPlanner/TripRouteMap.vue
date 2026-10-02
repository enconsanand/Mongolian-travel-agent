<script setup lang="ts">
import { formatMnt } from '~/utils/tripPlan'
import { STAY_TYPE_LABELS } from '~/constants/tripPlan'
import { API_ENDPOINTS } from '~/constants'
import type { EventView, ExtraStop, GeoPoint, PlaceView, Proposal, TransportSchedule } from '~/types/trip-plan'
import type { AppLocale } from '~/types/trip-planner'
import type { GoogleMaps } from '~/composables/useGoogleMaps'
import { fetchDrivingRoute, type DrivingRoute, type LatLng, type StopLegs } from '~/utils/drivingRoute'

/**
 * The current plan on a Google map: the route from stop to stop, the stays as ger pins, and round icons for the
 * events and the buses, trains and planes along the way. Hovering (or tapping) one shows its photo and details, and
 * an event or a transport stop can be added to the route from its card. Redraws whenever the plan changes.
 * The route follows real roads with Google's driving times when the Routes API has one.
 */
const {
  proposal,
  locale,
  extraStops = [],
} = defineProps<{
  proposal: Proposal
  locale: AppLocale
  /** Stops added from the map; the route goes through them until the agent's next plan includes them */
  extraStops?: ExtraStop[]
}>()

const emit = defineEmits<{ legs: [legs: StopLegs]; 'add-stop': [stop: ExtraStop] }>()

/** An event counts as along the way when it is this close to the route and overlaps the trip's dates */
const NEAR_ROUTE_KM = 40

const LABELS: Record<
  AppLocale,
  {
    noKey: string
    failed: string
    nights: string
    free: string
    route: string
    driving: string
    straight: string
    nearRoute: string
    addToRoute: string
    approximateDate: string
    otherDays: string
    onRoute: string
    transport: string
    departs: string
    modes: Record<string, string>
  }
> = {
  mn: {
    noKey: 'Газрын зураг харуулахын тулд Google Maps түлхүүр тохируулна уу.',
    failed: 'Газрын зураг ачаалж чадсангүй.',
    nights: 'шөнө',
    free: 'Үнэгүй',
    route: 'Аяллын маршрут',
    driving: 'Машинаар нийт',
    straight: 'Шулуун зай (замын мэдээлэл алга)',
    nearRoute: 'Замаас',
    addToRoute: 'Маршрутад нэмэх',
    approximateDate: 'огноо ойролцоо',
    otherDays: 'Таны аяллын өдрүүдэд биш, гэхдээ тэр сард болно',
    onRoute: 'Маршрутад нэмсэн',
    transport: 'Нийтийн тээвэр',
    departs: 'Хөдлөх цэг',
    modes: { bus: 'Автобус', train: 'Галт тэрэг', flight: 'Онгоц', shared_van: 'Хамтын микро' },
  },
  en: {
    noKey: 'Set a Google Maps key to show the map.',
    failed: 'The map could not be loaded.',
    nights: 'nights',
    free: 'Free',
    route: 'Trip route',
    driving: 'Total driving',
    straight: 'Straight lines (no road data)',
    nearRoute: 'Off the route by',
    addToRoute: 'Add to route',
    approximateDate: 'approximate date',
    otherDays: 'Not on your trip days, but in the same month',
    onRoute: 'On your route',
    transport: 'Public transport',
    departs: 'Departs from',
    modes: { bus: 'Bus', train: 'Train', flight: 'Flight', shared_van: 'Shared van' },
  },
}

// The map draws on a canvas, so it needs real colours: the brand tokens from tokens.css, per theme
const COLORS = {
  light: { route: '#1F3A5F', stop: '#1F3A5F', stayText: '#B07A1E', eventText: '#3F6B3A', transport: '#5B6472' },
  dark: { route: '#8FB4E3', stop: '#8FB4E3', stayText: '#E2B65C', eventText: '#9AC78C', transport: '#A3ABB7' },
}

const DARK_STYLE = [
  { elementType: 'geometry', stylers: [{ color: '#17202b' }] },
  { elementType: 'labels.text.fill', stylers: [{ color: '#a3abb7' }] },
  { elementType: 'labels.text.stroke', stylers: [{ color: '#10161f' }] },
  { featureType: 'road', elementType: 'geometry', stylers: [{ color: '#2b3747' }] },
  { featureType: 'water', elementType: 'geometry', stylers: [{ color: '#0f1a2a' }] },
  { featureType: 'poi', stylers: [{ visibility: 'off' }] },
]

const GER_GLYPH = 'M5 13 12 7l7 6M6.5 12v6h11v-6M10.5 18v-3.5h3V18'
const FLAG_GLYPH = 'M8 19V5m0 0h9l-2.2 3L17 11H8'
const BUS_GLYPH = 'M7 16V7a2 2 0 0 1 2-2h6a2 2 0 0 1 2 2v9M7 12h10M9 16v2M15 16v2'
const ROUND_ICON = 28

const { theme } = useTheme()
const container = ref<HTMLElement | null>(null)
const status = ref<'loading' | 'ready' | 'no-key' | 'failed'>('loading')
const route = ref<DrivingRoute | null>(null)
const routeChecked = ref(false)
const apiKey = useRuntimeConfig().public.googleMapsApiKey as string
const api = useApi()

let maps: GoogleMaps | null = null
let map: any = null
let overlays: any[] = []
let infoWindow: any = null
let drawSeq = 0
// A card opened by a click stays open until it is closed, unlike one shown on hover
let cardPinned = false

const latLng = (point?: GeoPoint) => (point ? { lng: point.coordinates[0], lat: point.coordinates[1] } : null)
const placeName = (id: string) => proposal.catalog.places[id]?.name ?? id

/** The places in the order the trip visits them, without repeating a place on consecutive days */
const stops = computed(() => {
  const ids: string[] = []
  const add = (id: string) => ids.at(-1) !== id && ids.push(id)
  proposal.days.forEach((day, index) => {
    if (index === 0) add(day.from_place_id)
    day.via_place_ids.forEach(add)
    add(day.to_place_id)
  })
  return ids
})

const PIN_W = 28
const PIN_H = 36

/**
 * A Google-style place pin (a drop with a white glyph) whose name sits to its right, like the places on Google Maps.
 * The label is centred on `labelOrigin`, so it is pushed right by half its estimated width.
 */
function placePin(color: string, glyph: string, name: string) {
  const svg =
    `<svg xmlns="http://www.w3.org/2000/svg" width="${PIN_W}" height="${PIN_H}" viewBox="0 0 24 31">` +
    `<path d="M12 30.5S1 18.6 1 11.5a11 11 0 0 1 22 0C23 18.6 12 30.5 12 30.5Z" fill="${color}" stroke="#fff" stroke-width="1.5"/>` +
    `<g transform="translate(2.4 1.6) scale(0.8)"><path d="${glyph}" fill="none" stroke="#fff" stroke-width="2" ` +
    `stroke-linecap="round" stroke-linejoin="round"/></g></svg>`
  const text = name.length > 32 ? `${name.slice(0, 31)}…` : name
  return {
    icon: {
      url: `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`,
      scaledSize: new maps.Size(PIN_W, PIN_H),
      anchor: new maps.Point(PIN_W / 2, PIN_H),
      labelOrigin: new maps.Point(PIN_W + 4 + text.length * 3.6, PIN_H / 2 - 2),
    },
    label: { text, color, fontSize: '13px', fontWeight: '600', className: 'map-pin-label' },
  }
}

/**
 * A round icon in the same style as the lettered stops, with a white glyph. `shift` moves it off its point (in
 * pixels, right and up), so a transport icon does not cover the stop it leaves from.
 */
function roundIcon(color: string, glyph: string, shift = 0) {
  const svg =
    `<svg xmlns="http://www.w3.org/2000/svg" width="${ROUND_ICON}" height="${ROUND_ICON}" viewBox="0 0 24 24">` +
    `<circle cx="12" cy="12" r="10.5" fill="${color}" stroke="#fff" stroke-width="2"/>` +
    `<g transform="translate(3 3) scale(0.75)"><path d="${glyph}" fill="none" stroke="#fff" stroke-width="2.2" ` +
    `stroke-linecap="round" stroke-linejoin="round"/></g></svg>`
  return {
    url: `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`,
    scaledSize: new maps.Size(ROUND_ICON, ROUND_ICON),
    anchor: new maps.Point(ROUND_ICON / 2 - shift, ROUND_ICON / 2 + shift),
  }
}

interface CardAction {
  label: string
  /** Already done (the stop is on the route): shown as a quiet note instead of a button */
  done: boolean
  run: () => void
}

/** The hover card, built as DOM nodes (never HTML strings) because names and descriptions come from the data */
function card(title: string, lines: string[], image?: string, action?: CardAction): HTMLElement {
  const root = document.createElement('div')
  root.style.cssText = 'width:220px;font-family:"Noto Sans",system-ui,sans-serif;color:#1c2430'
  if (image) {
    const img = document.createElement('img')
    img.src = image
    img.alt = ''
    img.style.cssText = 'display:block;width:100%;height:120px;object-fit:cover;border-radius:8px;margin-bottom:8px'
    root.appendChild(img)
  }
  const heading = document.createElement('div')
  heading.textContent = title
  heading.style.cssText = 'font-weight:600;font-size:14px;margin-bottom:4px'
  root.appendChild(heading)
  for (const line of lines.filter(Boolean)) {
    const row = document.createElement('div')
    row.textContent = line
    row.style.cssText = 'font-size:12px;line-height:1.5;color:#5b6472'
    root.appendChild(row)
  }
  if (action) {
    const button = document.createElement('button')
    button.type = 'button'
    button.textContent = action.done ? `✓ ${LABELS[locale].onRoute}` : `+ ${action.label}`
    button.disabled = action.done
    button.style.cssText =
      'margin-top:8px;width:100%;min-height:36px;border:0;border-radius:999px;font:600 13px "Noto Sans",sans-serif;' +
      (action.done ? 'background:#e6eee0;color:#3f6b3a' : 'background:#1f3a5f;color:#fff;cursor:pointer')
    button.addEventListener('click', (event) => {
      event.stopPropagation()
      action.run()
      cardPinned = false
      infoWindow.close()
    })
    root.appendChild(button)
  }
  return root
}

const isOnRoute = (id: string) => extraStops.some((stop) => stop.id === id)
const kmLabel = (km: number) => `${Math.round(km)} ${locale === 'mn' ? 'км' : 'km'}`

function addMarker(position: { lat: number; lng: number }, options: Record<string, unknown>, content: HTMLElement) {
  const marker = new maps.Marker({ map, position, ...options })
  // Hover peeks without moving the map; a click (or tap) also pans so the whole card is in view
  const show = (pan: boolean) => {
    // Reopening is what makes the map pan when the hover had already opened the card in place
    if (pan) infoWindow.close()
    infoWindow.setOptions({ disableAutoPan: !pan })
    infoWindow.setContent(content)
    infoWindow.open({ map, anchor: marker, shouldFocus: false })
  }
  marker.addListener('mouseover', () => !cardPinned && show(false))
  marker.addListener('mouseout', () => !cardPinned && infoWindow.close())
  marker.addListener('click', () => {
    cardPinned = true
    show(true)
  })
  overlays.push(marker)
}

function clear() {
  overlays.forEach((overlay) => overlay.setMap(null))
  overlays = []
  infoWindow?.close()
}

/** Real roads and driving times from the Routes API; straight lines between the stops when there is none */
async function drawRoute(ids: string[], points: LatLng[], color: string, seq: number) {
  if (points.length < 2) return
  const line = { strokeColor: color, strokeOpacity: 0.9, strokeWeight: 4 }
  const driving = await fetchDrivingRoute(apiKey, points)
  if (seq !== drawSeq) return
  route.value = driving
  routeChecked.value = true
  const path = driving?.path ?? points
  overlays.push(new maps.Polyline({ map, path, geodesic: !driving, zIndex: 5, ...line }))
  addEventsAlong(path, seq)
  addTransportAlong(path, seq)
  if (driving) {
    // A leg drawn straight has no driving time: the day keeps the planner's estimate
    const roadLegs = driving.legs
      .map((leg, i) => [`${ids[i]}>${ids[i + 1]}`, leg] as const)
      .filter(([, leg]) => !leg.straight)
    emit('legs', Object.fromEntries(roadLegs))
  }
}

/** Kilometres from a point to the segment a–b (flat-earth approximation, fine at these distances) */
function kmToSegment(p: LatLng, a: LatLng, b: LatLng): number {
  const kx = 111.32 * Math.cos((p.lat * Math.PI) / 180)
  const [ax, ay, bx, by] = [
    (a.lng - p.lng) * kx,
    (a.lat - p.lat) * 110.57,
    (b.lng - p.lng) * kx,
    (b.lat - p.lat) * 110.57,
  ]
  const [dx, dy] = [bx - ax, by - ay]
  const t = dx || dy ? Math.min(1, Math.max(0, -(ax * dx + ay * dy) / (dx * dx + dy * dy))) : 0
  return Math.hypot(ax + t * dx, ay + t * dy)
}

function kmToPath(point: LatLng, path: LatLng[]): number {
  let best = Infinity
  for (let i = 1; i < path.length; i++) best = Math.min(best, kmToSegment(point, path[i - 1]!, path[i]!))
  return best
}

function addEventMarker(event: EventView, position: LatLng, extra = '', addable = false, onTripDays = true) {
  const labels = LABELS[locale]
  addMarker(
    position,
    {
      icon: roundIcon(COLORS[theme.value].eventText, FLAG_GLYPH),
      title: event.name,
      // Events in the trip's month but not on its days stay visible, faded and below the rest
      opacity: onTripDays ? 1 : 0.45,
      zIndex: onTripDays ? 30 : 20,
    },
    card(
      event.name,
      [
        (event.start_date === event.end_date ? event.start_date : `${event.start_date} – ${event.end_date}`) +
          (event.date_confidence === 'approximate' ? ` (${labels.approximateDate})` : ''),
        event.ticket_price_mnt ? formatMnt(event.ticket_price_mnt, locale) : labels.free,
        extra,
        onTripDays ? '' : labels.otherDays,
        event.description ?? '',
      ],
      event.cover_image_url ?? undefined,
      addable
        ? {
            label: labels.addToRoute,
            done: isOnRoute(`event:${event.name}`),
            run: () => emit('add-stop', { id: `event:${event.name}`, name: event.name, location: event.location! }),
          }
        : undefined
    )
  )
}

/** Events near the road in the trip's month(s): the ones on trip days can be added, the rest are shown faded */
async function addEventsAlong(path: LatLng[], seq: number) {
  const first = proposal.days[0]?.date
  const last = proposal.days.at(-1)?.date
  if (!first || !last || path.length < 2) return
  const [year, month] = last.split('-').map(Number) as [number, number]
  const monthEnd = `${last.slice(0, 7)}-${String(new Date(Date.UTC(year, month, 0)).getUTCDate()).padStart(2, '0')}`
  const { data } = await api.get<(EventView & { _id?: string; id?: string })[]>(API_ENDPOINTS.TRAVEL.EVENTS, {
    query: { date_from: `${first.slice(0, 7)}-01`, date_to: monthEnd, limit: 200 },
    headers: { 'Accept-Language': locale },
  })
  if (seq !== drawSeq || !data) return
  const planned = new Set(Object.values(proposal.catalog.events).map((event) => event.name))
  for (const event of data) {
    const at = latLng(event.location)
    if (!at || planned.has(event.name)) continue
    const km = kmToPath(at, path)
    const onTripDays = event.start_date <= last && event.end_date >= first
    if (km <= NEAR_ROUTE_KM)
      addEventMarker(event, at, `${LABELS[locale].nearRoute} ~${kmLabel(km)}`, onTripDays, onTripDays)
  }
}

let placesById: Record<string, PlaceView> | null = null

/** Every place's name and location, loaded once: transport schedules name their towns by id only */
async function loadPlaces(): Promise<Record<string, PlaceView>> {
  if (placesById) return placesById
  const { data } = await api.get<(PlaceView & { id: string })[]>(API_ENDPOINTS.TRAVEL.PLACES, {
    query: { limit: 500 },
    headers: { 'Accept-Language': locale },
  })
  placesById = Object.fromEntries((data ?? []).map((place) => [place.id, place]))
  return placesById
}

function departures(times: string[]): string {
  return times.length > 3 ? `${times.slice(0, 3).join(', ')}…` : times.join(', ')
}

/**
 * Buses, trains, planes and shared vans leaving from the route's stops for towns on or near the route, as one round
 * icon beside each stop. Their card lists the departures; a town that is not a stop yet can be added to the route.
 */
async function addTransportAlong(path: LatLng[], seq: number) {
  const fromIds = [...new Set(stops.value)]
  const [places, ...results] = await Promise.all([
    loadPlaces(),
    ...fromIds.map((id) =>
      api.get<TransportSchedule[]>(API_ENDPOINTS.TRAVEL.SCHEDULES, {
        query: { from_place_id: id, limit: 50 },
        headers: { 'Accept-Language': locale },
      })
    ),
  ])
  if (seq !== drawSeq) return
  const labels = LABELS[locale]
  fromIds.forEach((fromId, index) => {
    const from = places[fromId] ?? proposal.catalog.places[fromId]
    const fromAt = latLng(from?.location)
    if (!from || !fromAt) return
    const near = (results[index]?.data ?? []).filter((schedule) => {
      const toAt = latLng(places[schedule.to_place_id]?.location)
      return stops.value.includes(schedule.to_place_id) || (toAt !== null && kmToPath(toAt, path) <= NEAR_ROUTE_KM)
    })
    if (!near.length) return
    const lines = near.flatMap((schedule) => [
      `${labels.modes[schedule.mode] ?? schedule.mode} → ${places[schedule.to_place_id]?.name ?? schedule.to_place_id} · ` +
        `${departures(schedule.departure_times)} · ${formatDuration(schedule.duration_min * 60)} · ${formatMnt(schedule.price_mnt, locale)}`,
    ])
    lines.push(`${labels.departs}: ${[...new Set(near.map((schedule) => schedule.departure_point))].join(', ')}`)
    // A town the transport reaches that is not on the route yet: offer it as a stop
    const newTown = near.find((schedule) => !stops.value.includes(schedule.to_place_id))
    const town = newTown ? places[newTown.to_place_id] : undefined
    addMarker(
      fromAt,
      { icon: roundIcon(COLORS[theme.value].transport, BUS_GLYPH, 14), title: labels.transport, zIndex: 25 },
      card(
        `${labels.transport} · ${from.name}`,
        lines,
        undefined,
        town?.location
          ? {
              label: `${labels.addToRoute}: ${town.name}`,
              done: isOnRoute(`place:${newTown!.to_place_id}`),
              run: () =>
                emit('add-stop', { id: `place:${newTown!.to_place_id}`, name: town.name, location: town.location! }),
            }
          : undefined
      )
    )
  })
}

function formatDuration(totalSec: number): string {
  const hours = Math.floor(totalSec / 3600)
  const minutes = Math.round((totalSec % 3600) / 60)
  const [h, m] = locale === 'mn' ? ['цаг', 'мин'] : ['h', 'min']
  return hours ? `${hours} ${h} ${minutes} ${m}` : `${minutes} ${m}`
}

function draw() {
  if (!map) return
  const seq = ++drawSeq
  clear()
  const colors = COLORS[theme.value]
  const labels = LABELS[locale]
  const catalog = proposal.catalog
  const bounds = new maps.LatLngBounds()

  const routed = stops.value.filter((id) => catalog.places[id]?.location)
  // Drive to where the night is spent: a place's point can sit somewhere no road reaches (a lake's centre)
  const sleepAt = (id: string) => {
    const night = proposal.days.find((day) => day.to_place_id === id && day.stay_id)
    return latLng(night?.stay_id ? catalog.stays[night.stay_id]?.location : undefined)
  }
  const points = routed.map((id) => sleepAt(id) ?? latLng(catalog.places[id]!.location)!)
  // Each stop added from the map goes between the two stops where it lengthens the trip least
  for (const extra of extraStops) {
    const at = latLng(extra.location)!
    if (points.length < 2 || routed.includes(extra.id)) continue
    let best = 1
    let bestCost = Infinity
    for (let i = 1; i < points.length; i++) {
      const cost = kmToSegment(at, points[i - 1]!, points[i]!)
      if (cost < bestCost) [best, bestCost] = [i, cost]
    }
    routed.splice(best, 0, extra.id)
    points.splice(best, 0, at)
    addMarker(
      at,
      { icon: roundIcon(colors.route, FLAG_GLYPH), title: extra.name, zIndex: 35 },
      card(extra.name, [LABELS[locale].onRoute])
    )
  }
  points.forEach((point) => bounds.extend(point))
  route.value = null
  routeChecked.value = false
  drawRoute(routed, points, colors.route, seq)

  // Stops, lettered in visiting order; the trip's start and end share a pin when they are the same place
  const seen = new Set<string>()
  stops.value.forEach((id) => {
    const position = latLng(catalog.places[id]?.location)
    if (!position || seen.has(id)) return
    seen.add(id)
    const place = catalog.places[id]!
    addMarker(
      position,
      {
        label: { text: String.fromCharCode(64 + seen.size), color: '#fff', fontSize: '11px', fontWeight: '700' },
        icon: {
          path: maps.SymbolPath.CIRCLE,
          scale: 10,
          fillColor: colors.stop,
          fillOpacity: 1,
          strokeColor: '#fff',
          strokeWeight: 2,
        },
        title: place.name,
      },
      card(place.name, [place.aimag])
    )
  })

  proposal.days.forEach((day) => {
    const stay = day.stay ? catalog.stays[day.stay.stay_id] : undefined
    const stayAt = latLng(stay?.location)
    if (day.stay && stay && stayAt) {
      bounds.extend(stayAt)
      addMarker(
        stayAt,
        { ...placePin(colors.stayText, GER_GLYPH, stay.name), title: stay.name, zIndex: 20 },
        card(
          stay.name,
          [
            `${STAY_TYPE_LABELS[stay.type]?.[locale] ?? stay.type} · ★ ${stay.rating} (${stay.reviews_count})`,
            `${day.stay.nights} ${labels.nights} · ${formatMnt(day.stay.total_mnt, locale)}`,
          ],
          stay.cover_image_url
        )
      )
    }
    day.event_ids.forEach((eventId) => {
      const event = catalog.events[eventId]
      const eventAt = latLng(event?.location)
      if (!event || !eventAt) return
      bounds.extend(eventAt)
      addEventMarker(event, eventAt)
    })
  })

  // Extra room at the top so a hover card above a northern pin is not cut off
  if (!bounds.isEmpty()) map.fitBounds(bounds, { top: 230, right: 48, bottom: 48, left: 48 })
}

/** The colour scheme is fixed when a map is created, so a theme change builds a new one */
function createMap() {
  clear()
  map = new maps.Map(container.value, {
    center: { lat: 47.9, lng: 103 },
    zoom: 5,
    disableDefaultUI: true,
    zoomControl: true,
    gestureHandling: 'cooperative',
    colorScheme: theme.value === 'dark' ? 'DARK' : 'LIGHT',
    styles: theme.value === 'dark' ? DARK_STYLE : null,
  })
  infoWindow = new maps.InfoWindow({ disableAutoPan: true })
  infoWindow.addListener('closeclick', () => (cardPinned = false))
  map.addListener('click', () => {
    cardPinned = false
    infoWindow.close()
  })
  draw()
}

onMounted(async () => {
  try {
    maps = await useGoogleMaps()
  } catch {
    status.value = 'failed'
    return
  }
  if (!maps || !container.value) {
    status.value = 'no-key'
    return
  }
  status.value = 'ready'
  createMap()
})

watch(
  () => [proposal.id, proposal.version, extraStops.length],
  () => draw()
)
watch(theme, () => {
  if (map) createMap()
})

onUnmounted(clear)
</script>

<template>
  <figure class="panel relative h-full min-h-80 overflow-hidden p-0" :aria-label="LABELS[locale].route">
    <div ref="container" class="absolute inset-0" />
    <p
      v-if="status === 'ready' && routeChecked"
      class="absolute top-3 left-3 rounded-full bg-surface px-3.5 py-1.5 text-sm shadow-card"
      aria-live="polite"
    >
      <template v-if="route">
        <i class="pi pi-car mr-1.5 text-brand" aria-hidden="true" />
        {{ LABELS[locale].driving }}:
        <span class="font-semibold">{{ formatDuration(route.durationSec) }}</span>
        · {{ Math.round(route.distanceM / 1000) }} {{ locale === 'mn' ? 'км' : 'km' }}
      </template>
      <span v-else class="text-ink-muted">{{ LABELS[locale].straight }}</span>
    </p>
    <figcaption
      v-if="status !== 'ready'"
      class="absolute inset-0 flex flex-col justify-center gap-3 bg-surface p-6 text-sm"
    >
      <p v-if="status === 'loading'" class="text-ink-muted">
        <i class="pi pi-spinner pi-spin mr-2" aria-hidden="true" />
        {{ LABELS[locale].route }}
      </p>
      <template v-else>
        <p class="text-ink-muted">{{ status === 'no-key' ? LABELS[locale].noKey : LABELS[locale].failed }}</p>
        <ol class="space-y-1 font-medium">
          <li v-for="(id, index) in stops" :key="`${id}-${index}`">
            {{ String.fromCharCode(65 + index) }}. {{ placeName(id) }}
          </li>
        </ol>
      </template>
    </figcaption>
  </figure>
</template>
