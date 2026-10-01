import type { PlanRequestBody, TravelStyle } from '~/types/trip-plan'
import { addDays, localIsoDate, MAX_TRIP_DAYS } from '~/utils/dates'

/** The planner's limit (PlanRequest.guests in back/app/modules/orchestrator/types.py) */
const MAX_GUESTS = 60
const DEFAULT_GUESTS = 2
const DEFAULT_DAYS = 3
/** With no date in the text, the trip starts a week from today */
const DEFAULT_START_IN_DAYS = 7
const MILLION = 1_000_000

/**
 * What the planner needs besides the free text, read from that text. Anything the traveller did not write falls
 * back to a default, and `stated` says which ones came from the text so the page can show what it assumed.
 */
export interface TripFacts {
  guests: number
  startDate: string
  endDate: string
  budgetMnt: number | null
  style: TravelStyle
  stated: { guests: boolean; dates: boolean; days: boolean; budget: boolean; style: boolean }
}

const GUESTS_RE = /(\d{1,2})\s*(хүн|хүүхэд|том хүн|people|persons?|guests?|adults?|of us)/i
const DAYS_RE = /(\d{1,2})\s*(хоног|өдөр|days?)/i
const NIGHTS_RE = /(\d{1,2})\s*(шөнө|nights?)/i
const MILLIONS_RE = /(\d+(?:[.,]\d+)?)\s*(сая|million|mill?|mln|m\b)/i
const AMOUNT_RE = /(\d[\d\s,]{4,})\s*(₮|төг|mnt|tugrik)/i
const MN_DATE_RE = /(\d{1,2})\s*(?:-р)?\s*сарын\s*(\d{1,2})/i
const NUMERIC_DATE_RE = /\b(\d{1,2})[./](\d{1,2})\b/
const EN_MONTHS = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
const EN_DATE_RE = /\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{1,2})\b/i

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value))
}

/** The next date (today or later) with this month and day, as YYYY-MM-DD */
function upcomingDate(month: number, day: number): string | null {
  if (month < 1 || month > 12 || day < 1 || day > 31) return null
  const today = localIsoDate()
  const year = Number(today.slice(0, 4))
  const candidate = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`
  return candidate >= today ? candidate : `${year + 1}${candidate.slice(4)}`
}

/** The first month and day written in the text: "10 сарын 5", "10.05" or "Oct 5" */
function readMonthDay(text: string): [month: number, day: number] | null {
  const english = text.match(EN_DATE_RE)
  if (english) return [EN_MONTHS.indexOf(english[1]!.toLowerCase()) + 1, Number(english[2])]
  const numeric = text.match(MN_DATE_RE) ?? text.match(NUMERIC_DATE_RE)
  return numeric ? [Number(numeric[1]), Number(numeric[2])] : null
}

function readStyle(text: string): TravelStyle | null {
  if (/хямд|хэмнэлт|budget|cheap|affordable/i.test(text)) return 'value'
  if (/наадам|соёл|naadam|culture|festival/i.test(text)) return 'culture'
  if (/vip|тансаг|тав тух|luxury|comfort|glamping/i.test(text)) return 'comfort'
  return null
}

export function readTripFacts(text: string): TripFacts {
  const guestsMatch = text.match(GUESTS_RE)
  const daysMatch = text.match(DAYS_RE)
  const nightsMatch = text.match(NIGHTS_RE)
  const millionsMatch = text.match(MILLIONS_RE)
  const amountMatch = text.match(AMOUNT_RE)
  const dateMatch = readMonthDay(text)
  const style = readStyle(text)

  const guests = guestsMatch ? clamp(Number(guestsMatch[1]), 1, MAX_GUESTS) : DEFAULT_GUESTS
  const days = daysMatch ? Number(daysMatch[1]) : nightsMatch ? Number(nightsMatch[1]) + 1 : DEFAULT_DAYS
  const startDate = (dateMatch && upcomingDate(dateMatch[0], dateMatch[1])) ?? localIsoDate(DEFAULT_START_IN_DAYS)

  let budgetMnt: number | null = null
  if (millionsMatch) budgetMnt = Math.round(Number(millionsMatch[1]!.replace(',', '.')) * MILLION)
  else if (amountMatch) budgetMnt = Number(amountMatch[1]!.replace(/[\s,]/g, ''))

  return {
    guests,
    startDate,
    endDate: addDays(startDate, clamp(days, 1, MAX_TRIP_DAYS) - 1),
    budgetMnt,
    style: style ?? 'comfort',
    stated: {
      guests: Boolean(guestsMatch),
      dates: Boolean(dateMatch),
      days: Boolean(daysMatch ?? nightsMatch),
      budget: budgetMnt !== null,
      style: style !== null,
    },
  }
}

export function toPlanRequestBody(facts: TripFacts, text: string): PlanRequestBody {
  return {
    text: text.trim(),
    guests: facts.guests,
    start_date: facts.startDate,
    end_date: facts.endDate,
    budget_mnt: facts.budgetMnt,
    style: facts.style,
  }
}
