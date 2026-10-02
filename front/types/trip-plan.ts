import type { AppLocale } from '~/types/trip-planner'

export type TravelStyle = 'value' | 'comfort' | 'culture'

export type PlanWarning = 'unresolved_place' | 'event_off_dates' | 'no_availability' | 'over_budget' | 'too_many_places'

/** Body of POST /planner/proposals (the language comes from Accept-Language) */
export interface PlanRequestBody {
  text: string
  guests: number
  start_date: string
  end_date: string
  budget_mnt: number | null
  style: TravelStyle
}

export interface ResolvedPlace {
  query: string
  place_id: string | null
  status: 'included' | 'unresolved'
}

export interface StayPick {
  stay_id: string
  unit_type: string
  units: number
  nights: number
  total_mnt: number
}

/** How the group travels on a travel day, picked by the planner: the car (fuel) or a timetabled service */
export interface DayTransport {
  mode: 'car' | 'bus' | 'train' | 'flight' | 'shared_van'
  schedule_id: string | null
  operator: string | null
  departure_time: string | null
  duration_min: number
  /** For the whole group */
  total_mnt: number
}

export type TransportKind = 'public' | 'with_driver' | 'self_drive' | 'own_car'

/** One way to travel the whole trip, priced for the group */
export interface TransportOption {
  kind: TransportKind
  vehicle: string | null
  operator: string | null
  vehicles: number
  days: number
  rent_mnt: number
  fuel_mnt: number
  tickets_mnt: number
  total_mnt: number
}

/** The way of travel the planner picked, why, and the ones it priced but did not pick */
export interface TransportPlan {
  chosen: TransportOption
  reason: 'asked' | 'style' | 'budget' | 'over_budget'
  alternatives: TransportOption[]
}

export interface PlanDay {
  day: number
  date: string
  from_place_id: string
  to_place_id: string
  via_place_ids: string[]
  route_id: string | null
  distance_km: number
  drive_time_min: number
  /** Set on the first night of each stay block */
  stay: StayPick | null
  /** The stay slept in that night */
  stay_id: string | null
  event_ids: string[]
  transport?: DayTransport | null
  note: string | null
}

export interface TripFit {
  feasible: boolean
  min_nights: number
  drive_min: number
  place_id: string | null
}

export interface PlanTotals {
  stays_mnt: number
  events_mnt: number
  transport_mnt?: number
  total_mnt: number
  budget_mnt: number | null
  within_budget: boolean
}

/** A GeoJSON point: coordinates are [longitude, latitude] */
export interface GeoPoint {
  type: 'Point'
  coordinates: [number, number]
}

export interface PlaceView {
  name: string
  location?: GeoPoint
  aimag: string
  region: string
  kind: string
}

export interface ImageCredit {
  url: string
  author: string
  license: string
  source: string
}

export interface StayReview {
  author: string
  rating: number
  text: string
}

export interface StayChoice {
  id: string
  name: string
  type: StayView['type']
  rating: number
  reviews_count: number
  reviews?: StayReview[]
  cover_image_url: string | null
  images?: ImageCredit[]
  meals: boolean
  total_mnt: number
  km: number
  selected: boolean
}

export interface StayView {
  name: string
  location?: GeoPoint
  type: 'ger_camp' | 'guesthouse' | 'hotel' | 'house'
  aimag: string
  rating: number
  reviews_count: number
  reviews?: StayReview[]
  cover_image_url: string
  images: ImageCredit[]
  check_in: string
  check_out: string
}

export interface EventView {
  name: string
  description?: string
  category: string
  location?: GeoPoint
  /** `exact` when the date was checked against a published calendar */
  date_confidence?: 'exact' | 'approximate'
  start_date: string
  end_date: string
  ticket_price_mnt: number
  cover_image_url?: string | null
  phone?: string | null
  url?: string | null
}

export interface Proposal {
  /** Returned only to the creator, never by a public read. */
  claim_token?: string
  id: string
  version: number
  request: PlanRequestBody & { lang: AppLocale }
  changes: string[]
  places: ResolvedPlace[]
  days: PlanDay[]
  totals: PlanTotals
  warnings: PlanWarning[]
  /** Missing on plans saved before the drive-time check */
  fit?: TripFit
  /** Missing on plans made before transport was priced */
  transport?: TransportPlan | null
  summary: string
  accepted: boolean
  expires_at: string
  catalog: {
    places: Record<string, PlaceView>
    stays: Record<string, StayView>
    events: Record<string, EventView>
  }
}

export interface AcceptResult {
  trip_id: string
  checkout_id: string
}

/** A place the traveller added to the route from the map (an event, a transport stop), before the agent replans */
export interface ExtraStop {
  id: string
  name: string
  location: GeoPoint
}

/** A scheduled bus, train, plane or shared van between two towns (GET /transport/schedules) */
export interface TransportSchedule {
  mode: string
  operator: string
  from_place_id: string
  to_place_id: string
  departure_point: string
  departure_times: string[]
  duration_min: number
  price_mnt: number
}
