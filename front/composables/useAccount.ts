import { ACCOUNT_MESSAGES } from '~/constants/account'
import { formatMnt } from '~/utils/tripPlan'

/** "+97699112233" reads as "+976 9911 2233"; emails and anything unexpected pass through unchanged. */
export function formatContact(value: string) {
  const match = /^\+976(\d{4})(\d{4})$/.exec(value)
  return match ? `+976 ${match[1]} ${match[2]}` : value
}

export function useAccountMessages() {
  const locale = useAppLocale()
  const messages = computed(() => ACCOUNT_MESSAGES[locale.value])
  const money = (amount: number) => formatMnt(amount, locale.value)
  const date = (value: string) => {
    // Browsers ship no Mongolian month names, so mn-MN would fall back to English; spell it like the planner does
    if (locale.value === 'mn') {
      const [y, mo, d] = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Ulaanbaatar' })
        .format(new Date(value))
        .split('-')
      return `${y} оны ${Number(mo)} сарын ${Number(d)}`
    }
    return new Intl.DateTimeFormat('en-GB', { dateStyle: 'medium', timeZone: 'Asia/Ulaanbaatar' }).format(
      new Date(value)
    )
  }
  /** "1 night" / "2 nights"; Mongolian nouns do not change, so both forms are the same there. */
  const count = (n: number, noun: 'people' | 'nights' | 'rooms') =>
    `${n} ${n === 1 ? messages.value.one[noun] : messages.value[noun]}`
  return { locale, messages, money, date, count, contact: formatContact }
}

/** Page-scoped state: account switches never reuse a previous traveller's data. */
export function useAccountResource<T>(path: string) {
  const api = useApi()
  const { locale } = useAccountMessages()
  const auth = useCookieAuth()
  const data = ref<T | null>(null)
  const loading = ref(true)
  const failed = ref(false)
  /** The record is missing or belongs to someone else: retrying will not help, unlike `failed`. */
  const notFound = ref(false)
  let request = 0
  async function load() {
    const ticket = ++request
    loading.value = true
    failed.value = false
    notFound.value = false
    const result = await api.get<T>(path, { headers: { 'Accept-Language': locale.value } })
    if (ticket !== request) return
    data.value = result.data
    notFound.value = result.error?.statusCode === 404
    failed.value = !!result.error && !notFound.value
    loading.value = false
  }
  onMounted(load)
  watch(locale, load)
  watch(auth.authToken, () => {
    ++request
    data.value = null
  })
  onUnmounted(() => {
    ++request
  })
  return { data, loading, failed, notFound, load }
}
