import type { TravelPeriod } from '~/types/trip-planner'

export function localIsoDate(offsetDays = 0): string {
  const date = new Date()
  date.setDate(date.getDate() + offsetDays)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

export function travelPeriodError(period: TravelPeriod): 'missing' | 'outOfOrder' | null {
  if (!period.startDate || !period.endDate) return 'missing'
  if (period.endDate < period.startDate) return 'outOfOrder'
  return null
}
