export function formatMnt(amount: number, locale: 'mn' | 'en'): string {
  const formatted = new Intl.NumberFormat(locale === 'mn' ? 'mn-MN' : 'en-US').format(amount)
  return `${formatted}₮`
}

/** "6 сарын 5" / "Jun 5": browsers ship no Mongolian month names, so mn-MN would print English ones. */
export function formatMonthDay(isoDate: string, locale: 'mn' | 'en'): string {
  const date = new Date(`${isoDate}T00:00:00`)
  if (locale === 'mn') return `${date.getMonth() + 1} сарын ${date.getDate()}`
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

const MN_WEEKDAYS = ['Ням', 'Даваа', 'Мягмар', 'Лхагва', 'Пүрэв', 'Баасан', 'Бямба']

/** "Даваа, 6 сарын 5" / "Mon, Jun 5" */
export function formatDayDate(isoDate: string, locale: 'mn' | 'en'): string {
  const date = new Date(`${isoDate}T00:00:00`)
  if (locale === 'mn') return `${MN_WEEKDAYS[date.getDay()]}, ${formatMonthDay(isoDate, locale)}`
  return date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })
}

export function formatDriveTime(minutes: number, locale: 'mn' | 'en'): string {
  const hours = Math.floor(minutes / 60)
  const rest = minutes % 60
  if (locale === 'mn') return hours ? `${hours} цаг ${rest} мин` : `${rest} мин`
  return hours ? `${hours} h ${rest} min` : `${rest} min`
}
