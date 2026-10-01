import type { PlanDay, PlanTotals, StayView } from './trip-plan'

export interface Profile {
  id: string
  email: string | null
  phone: string | null
  first_name: string
  last_name: string
}

export interface Invoice {
  id: string
  trip_id: string
  trip_title: string
  checkout_id: string | null
  reference: string
  amount_mnt: number
  status: string
  provider: string
  paid_at: string | null
  lines: { label: string; qty: number; total_mnt: number }[]
}

export interface MyTrip {
  id: string
  title: string
  start_date: string
  end_date: string
  party: { adults: number; children: number }
  status: string
  cover_image_url?: string | null
  total_mnt?: number
  route?: string[]
}

export interface TripBooking {
  id: string
  status: string
  kind: string
  stay_id: string | null
  unit_type: string | null
  units?: number | null
  check_in: string | null
  check_out: string | null
  nights: number | null
  guests: number | null
  total_price_mnt: number
}

export interface MyTripDetail extends MyTrip {
  can_resume: boolean
  plan: { days: PlanDay[]; totals: PlanTotals; summary: string; request: { guests: number } } | null
  itinerary: { days: { day: number; date: string; from_place_id: string; to_place_id: string }[] } | null
  stays: Record<string, StayView>
  places: Record<string, { name: string }>
  bookings: TripBooking[]
  checkouts: { id: string; status: string; total_mnt: number; expires_at: string }[]
  invoices: Invoice[]
}
