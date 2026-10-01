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
