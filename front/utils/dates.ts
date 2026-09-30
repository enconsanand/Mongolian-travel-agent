import type { TravelPeriod } from '~/types/trip-planner'

export function localIsoDate(offsetDays = 0): string {
  const date = new Date()
  date.setDate(date.getDate() + offsetDays)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

/** The planner's limit (MAX_TRIP_DAYS in back/app/modules/orchestrator/types.py), counting both ends */
export const MAX_TRIP_DAYS = 30

/** ``isoDate`` moved by ``days`` */
export function addDays(isoDate: string, days: number): string {
  const date = new Date(`${isoDate}T00:00:00Z`)
  date.setUTCDate(date.getUTCDate() + days)
  return date.toISOString().slice(0, 10)
}

export function travelPeriodError(period: TravelPeriod): 'missing' | 'outOfOrder' | 'tooLong' | null {
  if (!period.startDate || !period.endDate) return 'missing'
  if (period.endDate < period.startDate) return 'outOfOrder'
  if (period.endDate > addDays(period.startDate, MAX_TRIP_DAYS - 1)) return 'tooLong'
  return null
}
