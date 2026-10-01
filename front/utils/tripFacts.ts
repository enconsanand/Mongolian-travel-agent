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
  /** `dates` is a real from–to range, not a number of nights on its own */
  stated: { place: boolean; guests: boolean; dates: boolean; days: boolean; budget: boolean; style: boolean }
}

const GUESTS_RE = /(\d{1,2})\s*(хүн|хүүхэд|том хүн|people|persons?|guests?|adults?|of us)/i
const DAYS_RE = /(\d{1,2})\s*(хоног|өдөр|days?)/i
const NIGHTS_RE = /(\d{1,2})\s*(шөнө|nights?)/i
const MILLIONS_RE = /(\d+(?:[.,]\d+)?)\s*(сая|million|mill?|mln|m\b)/i
/** "500 мянга", "500 thousand": one thousand tugrik, not one million */
const THOUSANDS_RE = /(\d+(?:[.,]\d+)?)\s*(мянга(?:н)?|thousand|k\b)/i
const HALF_MILLION_RE = /хагас\s*сая|half\s+a\s+million/i
/** "таван зуун мянга", "хоёр сая": a unit word keeps "хоёр хүн" from looking like a budget */
const MONEY_UNIT_RE = /мянга|сая|thousand|million/i
const NUMBER_WORDS: Record<string, number> = {
  нэг: 1,
  нэгэн: 1,
  хоёр: 2,
  гурав: 3,
  гурван: 3,
  дөрөв: 4,
  дөрвөн: 4,
  тав: 5,
  таван: 5,
  зургаа: 6,
  зургаан: 6,
  долоо: 7,
  долоон: 7,
  найм: 8,
  найман: 8,
  ес: 9,
  есөн: 9,
  арав: 10,
  арван: 10,
  хорь: 20,
  хорин: 20,
  гуч: 30,
  гучин: 30,
  дөч: 40,
  дөчин: 40,
  тавь: 50,
  тавин: 50,
  жар: 60,
  жаран: 60,
  дал: 70,
  далан: 70,
  ная: 80,
  наян: 80,
  ер: 90,
  ерэн: 90,
  one: 1,
  two: 2,
  three: 3,
  four: 4,
  five: 5,
  six: 6,
  seven: 7,
  eight: 8,
  nine: 9,
  ten: 10,
  twenty: 20,
  thirty: 30,
  forty: 40,
  fifty: 50,
}
const AMOUNT_RE = /(\d[\d\s,]{4,})\s*(₮|төг|mnt|tugrik)/i
const EN_MONTHS = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
const EN_MONTH = 'jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec'
/** "10 сарын 5-наас 12", "10 сарын 5-наас 11 сарын 2", "2-оос 9" */
const MN_RANGE_RE = new RegExp(
  String.raw`(\d{1,2})\s*(?:-р)?\s*сарын\s*(\d{1,2})(?:\s*-\s*н[ыд])?\s*(?:(?:-|\s)?(?:наас|нээс|ноос|нөөс|аас|ээс|оос|өөс)|-|–|—)\s*(?:(\d{1,2})\s*(?:-р)?\s*сарын\s*)?(\d{1,2})(?:\s*-\s*н[ыд])?(?!\s*(?:хоног|өдөр|шөнө|хүн|сая))`,
  'i'
)
const MN_START_SPAN_RE =
  /(\d{1,2})\s*(?:-р)?\s*сарын\s*(\d{1,2})(?:\s*(?:наас|нээс|ноос|нөөс|аас|ээс|оос|өөс|-|–|—))?.{0,24}?(\d{1,2})\s*(хоног|өдөр|шөнө)/i
const MN_SPAN_BEFORE_RE =
  /(\d{1,2})\s*(хоног|өдөр|шөнө).{0,40}?(\d{1,2})\s*(?:-р)?\s*сарын\s*(\d{1,2})(?!\s*(?:наас|нээс|ноос|нөөс|аас|ээс|оос|өөс))/i
const NUM_RANGE_RE = /\b(\d{1,2})[./](\d{1,2})\s*[-–—]\s*(?:(\d{1,2})[./])?(\d{1,2})\b/
const EN_RANGE_RE = new RegExp(
  String.raw`\b(${EN_MONTH})[a-z]*\.?\s+(\d{1,2})\s*(?:to|-|–|—)\s*(?:(${EN_MONTH})[a-z]*\.?\s+)?(\d{1,2})\b`,
  'i'
)
const EN_START_SPAN_RE = new RegExp(
  String.raw`(${EN_MONTH})[a-z]*\.?\s+(\d{1,2}).{0,24}?(\d{1,2})\s*(days?|nights?)`,
  'i'
)
const EN_SPAN_BEFORE_RE = new RegExp(
  String.raw`(\d{1,2})\s*(days?|nights?).{0,24}?(${EN_MONTH})[a-z]*\.?\s+(\d{1,2})\b`,
  'i'
)
const UNLIMITED_RE = /хязгааргүй|хязгаар\s*байхгүй|unlimited|no\s+limit/i
const PLACE_RE = /[\p{L}]{3,}\s*(?:рүү|руу|нуур|аймаг)/u
const QUESTION_RE =
  /[?？]\s*$|\b(юу|яаж|яагаад|ямар|хэн)\b|(?:^|\s)(уу|үү)\s*$|\b(what|why|how|who|when|where)\b|\b(can|could|would)\s+you\b/i
const NOT_A_PLACE = new Set([
  'хүн',
  'хүүхэд',
  'хоног',
  'өдөр',
  'шөнө',
  'сарын',
  'сая',
  'мянга',
  'мянган',
  'дотор',
  'төгрөг',
  'төг',
  'хязгааргүй',
  'хязгаар',
  'байхгүй',
  'хооронд',
  'хүртэл',
  'аялал',
  'аялах',
  'явах',
  'явъя',
  'хэмнэлттэй',
  'хямд',
  'тансаг',
  'морь',
  'унах',
  'үзэх',
  'наадам',
  'гэр',
  'бүл',
  'бүлээрээ',
  'нуур',
  'рүү',
  'руу',
  'аймаг',
  'наас',
  'нээс',
  'ноос',
  'нөөс',
  'аас',
  'ээс',
  'оос',
  'өөс',
  'people',
  'person',
  'persons',
  'guests',
  'guest',
  'adults',
  'adult',
  'days',
  'day',
  'nights',
  'night',
  'from',
  'with',
  'and',
  'the',
  'for',
  'budget',
  'cheap',
  'family',
  'horse',
  'riding',
  'lake',
  'thousand',
  'million',
  'under',
  'within',
  'jan',
  'feb',
  'mar',
  'apr',
  'may',
  'jun',
  'jul',
  'aug',
  'sep',
  'oct',
  'nov',
  'dec',
])

/** "таван зуун мянга" is 500_000. Returns null when the text names no amount. */
function readWordAmount(text: string): number | null {
  if (!MONEY_UNIT_RE.test(text)) return null
  const tokens = text.toLowerCase().match(/[a-zа-яөүё]+/gi) ?? []
  let total = 0
  let current = 0
  let saw = false
  for (const token of tokens) {
    const ones = NUMBER_WORDS[token]
    if (ones !== undefined) {
      current += ones
      saw = true
    } else if (token === 'зуу' || token === 'зуун' || token === 'hundred') {
      current = (current || 1) * 100
      saw = true
    } else if (token === 'мянга' || token === 'мянган' || token === 'thousand') {
      total += (current || 1) * 1_000
      current = 0
      saw = true
    } else if (token === 'сая' || token === 'million') {
      total += (current || 1) * MILLION
      current = 0
      saw = true
    }
  }
  const amount = total + current
  return saw && amount > 0 ? amount : null
}

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

function isoDate(year: number, month: number, day: number): string | null {
  if (month < 1 || month > 12 || day < 1 || day > 31) return null
  const date = new Date(Date.UTC(year, month - 1, day))
  if (date.getUTCMonth() !== month - 1) return null
  return date.toISOString().slice(0, 10)
}

/** Start and end, inclusive. An end that falls before the start rolls into the next year. */
function span(
  startMonth: number,
  startDay: number,
  endMonth: number,
  endDay: number
): { start: string; end: string } | null {
  const start = upcomingDate(startMonth, startDay)
  if (!start) return null
  const year = Number(start.slice(0, 4))
  let end = isoDate(year, endMonth, endDay)
  if (!end) return null
  if (end < start) end = isoDate(year + 1, endMonth, endDay)
  if (!end) return null
  const maxEnd = addDays(start, MAX_TRIP_DAYS - 1)
  if (end > maxEnd) end = maxEnd
  return end < start ? null : { start, end }
}

function monthIndex(name: string): number {
  return EN_MONTHS.indexOf(name.toLowerCase()) + 1
}

function addSpan(start: string, amount: number, unit: string): { start: string; end: string } | null {
  const nights = /шөнө|night/i.test(unit)
  const days = clamp(nights ? amount + 1 : amount, 1, MAX_TRIP_DAYS)
  return { start, end: addDays(start, days - 1) }
}

/** Two "10 сарын 3 … 10 сарын 8" pairs are a range, whatever dash or comma sits between them */
function mongolianPairs(text: string): { month: number; day: number }[] {
  return [...text.matchAll(/(\d{1,2})\s*(?:-р)?\s*сарын\s*(\d{1,2})/gi)].map((match) => ({
    month: Number(match[1]),
    day: Number(match[2]),
  }))
}

function englishPairs(text: string): { month: number; day: number }[] {
  const pair = new RegExp(String.raw`\b(${EN_MONTH})[a-z]*\.?\s+(\d{1,2})\b`, 'gi')
  return [...text.matchAll(pair)].map((match) => ({ month: monthIndex(match[1]!), day: Number(match[2]) }))
}

function readDateRange(text: string): { start: string; end: string } | null {
  const normalized = text.replace(/[\u2010-\u2015\u2212\uFE58\uFE63\uFF0D~～]/g, '-')
  const mnPairs = mongolianPairs(normalized)
  if (mnPairs.length >= 2) {
    const found = span(mnPairs[0]!.month, mnPairs[0]!.day, mnPairs[1]!.month, mnPairs[1]!.day)
    if (found) return found
  }
  const enPairs = englishPairs(normalized)
  if (enPairs.length >= 2) {
    const found = span(enPairs[0]!.month, enPairs[0]!.day, enPairs[1]!.month, enPairs[1]!.day)
    if (found) return found
  }

  const mn = normalized.match(MN_RANGE_RE)
  if (mn) {
    const found = span(Number(mn[1]), Number(mn[2]), Number(mn[3] ?? mn[1]), Number(mn[4]))
    if (found) return found
  }
  const numeric = normalized.match(NUM_RANGE_RE)
  if (numeric) {
    const found = span(Number(numeric[1]), Number(numeric[2]), Number(numeric[3] ?? numeric[1]), Number(numeric[4]))
    if (found) return found
  }
  const english = normalized.match(EN_RANGE_RE)
  if (english) {
    const startMonth = monthIndex(english[1]!)
    const found = span(
      startMonth,
      Number(english[2]),
      english[3] ? monthIndex(english[3]) : startMonth,
      Number(english[4])
    )
    if (found) return found
  }

  const startSpan = normalized.match(MN_START_SPAN_RE)
  if (startSpan) {
    const start = upcomingDate(Number(startSpan[1]), Number(startSpan[2]))
    if (start) return addSpan(start, Number(startSpan[3]), startSpan[4]!)
  }
  const spanBefore = normalized.match(MN_SPAN_BEFORE_RE)
  if (spanBefore) {
    const start = upcomingDate(Number(spanBefore[3]), Number(spanBefore[4]))
    if (start) return addSpan(start, Number(spanBefore[1]), spanBefore[2]!)
  }
  const enStart = normalized.match(EN_START_SPAN_RE)
  if (enStart) {
    const start = upcomingDate(monthIndex(enStart[1]!), Number(enStart[2]))
    if (start) return addSpan(start, Number(enStart[3]), enStart[4]!)
  }
  const enBefore = normalized.match(EN_SPAN_BEFORE_RE)
  if (enBefore) {
    const start = upcomingDate(monthIndex(enBefore[3]!), Number(enBefore[4]))
    if (start) return addSpan(start, Number(enBefore[1]), enBefore[2]!)
  }
  return null
}

/** Somewhere to go, not a guest count, a date, or a greeting */
export function mentionsPlace(text: string): boolean {
  if (PLACE_RE.test(text)) return true
  if (isUnrelatedQuestion(text)) return false
  const words = text.match(/\p{L}{3,}/gu) ?? []
  return words.some((word) => !NOT_A_PLACE.has(word.toLowerCase()))
}

/** A question that is not an answer to the trip brief: weather, who we are, and the like */
export function isUnrelatedQuestion(text: string): boolean {
  return QUESTION_RE.test(text.trim())
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
  const thousandsMatch = text.match(THOUSANDS_RE)
  const amountMatch = text.match(AMOUNT_RE)
  const range = readDateRange(text)
  const style = readStyle(text)

  const guests = guestsMatch ? clamp(Number(guestsMatch[1]), 1, MAX_GUESTS) : DEFAULT_GUESTS
  const days = daysMatch ? Number(daysMatch[1]) : nightsMatch ? Number(nightsMatch[1]) + 1 : DEFAULT_DAYS
  const startDate = range?.start ?? localIsoDate(DEFAULT_START_IN_DAYS)
  const endDate = range?.end ?? addDays(startDate, clamp(days, 1, MAX_TRIP_DAYS) - 1)

  let budgetMnt: number | null = null
  if (millionsMatch) budgetMnt = Math.round(Number(millionsMatch[1]!.replace(',', '.')) * MILLION)
  else if (thousandsMatch) budgetMnt = Math.round(Number(thousandsMatch[1]!.replace(',', '.')) * 1_000)
  else if (HALF_MILLION_RE.test(text)) budgetMnt = MILLION / 2
  else if (amountMatch) budgetMnt = Number(amountMatch[1]!.replace(/[\s,]/g, ''))
  else budgetMnt = readWordAmount(text)

  return {
    guests,
    startDate,
    endDate,
    budgetMnt,
    style: style ?? 'comfort',
    stated: {
      place: mentionsPlace(text),
      guests: Boolean(guestsMatch),
      dates: range !== null,
      days: Boolean(daysMatch ?? nightsMatch),
      budget: budgetMnt !== null || UNLIMITED_RE.test(text),
      style: style !== null,
    },
  }
}

const EN_MONTH_LABELS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

/** A range the chat can show back, and that readDateRange accepts */
export function formatTripRange(startIso: string, endIso: string, locale: 'mn' | 'en'): string {
  const [, startMonth, startDay] = startIso.split('-').map(Number)
  const [, endMonth, endDay] = endIso.split('-').map(Number)
  if (locale === 'mn') return `${startMonth} сарын ${startDay}-наас ${endMonth} сарын ${endDay}`
  return `${EN_MONTH_LABELS[startMonth! - 1]} ${startDay} to ${EN_MONTH_LABELS[endMonth! - 1]} ${endDay}`
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
