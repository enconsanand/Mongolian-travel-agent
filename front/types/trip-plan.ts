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

export interface PlanTotals {
  stays_mnt: number
  events_mnt: number
  total_mnt: number
  budget_mnt: number | null
  within_budget: boolean
}

export interface PlaceView {
  name: string
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

export interface StayView {
  name: string
  type: 'ger_camp' | 'guesthouse' | 'hotel' | 'house'
  aimag: string
  rating: number
  reviews_count: number
  cover_image_url: string
  images: ImageCredit[]
  check_in: string
  check_out: string
}

export interface EventView {
  name: string
  category: string
  start_date: string
  end_date: string
  ticket_price_mnt: number
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
