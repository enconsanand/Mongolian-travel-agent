import type { AppLocale } from '~/types/trip-planner'

export type TravelStyle = 'value' | 'comfort' | 'culture'

export type PlanWarning = 'unresolved_place' | 'no_availability' | 'over_budget' | 'too_many_places'

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
