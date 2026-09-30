import type { PlanRequestBody, TravelStyle } from '~/types/trip-plan'
import type { PreferenceSelection, TripPreferences } from '~/types/trip-planner'

const MILLION = 1_000_000

const BUDGET_PRESETS_MNT: Record<string, number | null> = {
  'up-to-2m': 2 * MILLION,
  'up-to-3-5m': 3.5 * MILLION,
  'up-to-5m': 5 * MILLION,
  unlimited: null,
}

const STYLES: TravelStyle[] = ['value', 'comfort', 'culture']

function groupSize(selection: PreferenceSelection): number {
  return selection.kind === 'custom' ? Math.round(selection.amount) : Number(selection.optionId)
}

/** Total budget in MNT; the custom field is entered in millions */
function budget(selection: PreferenceSelection): number | null {
  if (selection.kind === 'custom') return Math.round(selection.amount * MILLION)
  return BUDGET_PRESETS_MNT[selection.optionId] ?? null
}

function style(selection: PreferenceSelection): TravelStyle {
  const id = selection.kind === 'preset' ? selection.optionId : ''
  return STYLES.find((option) => option === id) ?? 'comfort'
}

/** The planner request from the page's preferences; call only once every preference is chosen */
export function toPlanRequestBody(preferences: TripPreferences, text: string): PlanRequestBody {
  const { groupSize: size, budget: total, travelStyle, duration } = preferences
  if (!size || !total || !travelStyle) throw new Error('preferences are incomplete')
  return {
    text: text.trim(),
    guests: groupSize(size),
    start_date: duration.startDate,
    end_date: duration.endDate,
    budget_mnt: budget(total),
    style: style(travelStyle),
  }
}

export function formatMnt(amount: number, locale: 'mn' | 'en'): string {
  const formatted = new Intl.NumberFormat(locale === 'mn' ? 'mn-MN' : 'en-US').format(amount)
  return `${formatted}₮`
}

export function formatDriveTime(minutes: number, locale: 'mn' | 'en'): string {
  const hours = Math.floor(minutes / 60)
  const rest = minutes % 60
  if (locale === 'mn') return hours ? `${hours} цаг ${rest} мин` : `${rest} мин`
  return hours ? `${hours} h ${rest} min` : `${rest} min`
}
