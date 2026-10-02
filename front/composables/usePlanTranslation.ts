import type { Ref } from 'vue'
import { API_ENDPOINTS } from '~/constants'
import type { Proposal } from '~/types/trip-plan'
import type { AppLocale } from '~/types/trip-planner'

/** Translations already fetched this session, by target language and source text */
const memo = new Map<string, string>()

/**
 * The plan's summary and day notes are written once, in the language the plan was asked in. When the page is
 * shown in the other language, Orchu (oyu MT, through our backend) translates them. Until the translation
 * arrives, or if it fails, the original text stays on screen.
 */
export function usePlanTranslation(proposal: Ref<Proposal | null>, locale: Ref<AppLocale>) {
  const api = useApi()
  const translating = ref(false)
  const failed = ref(false)
  const version = ref(0)

  const source = computed(() => proposal.value?.request.lang ?? locale.value)
  const texts = computed(() => {
    const plan = proposal.value
    if (!plan) return []
    return [plan.summary, ...plan.days.map((day) => day.note ?? '')]
  })
  const needed = computed(() => source.value !== locale.value && texts.value.some((text) => text.trim()))

  const key = (target: AppLocale, text: string) => `${target}\u0000${text}`

  async function translate() {
    failed.value = false
    // The memo is module state: keep it in the browser, never shared between server requests
    if (!import.meta.client || !needed.value) return
    const target = locale.value
    const missing = [...new Set(texts.value.filter((text) => text.trim() && !memo.has(key(target, text))))]
    if (!missing.length) return
    translating.value = true
    const { data, error } = await api.post<{ texts: string[] }>(API_ENDPOINTS.VOICE.TRANSLATE, {
      texts: missing,
      source: source.value,
      target,
    })
    translating.value = false
    if (error || !data || data.texts.length !== missing.length) {
      failed.value = true
      return
    }
    missing.forEach((text, i) => memo.set(key(target, text), data.texts[i]!))
    version.value++
  }

  watch([texts, locale], () => void translate(), { immediate: true })

  /** The proposal with its prose in the page language where a translation is ready */
  const shown = computed<Proposal | null>(() => {
    void version.value
    const plan = proposal.value
    if (!plan || !needed.value) return plan
    const target = locale.value
    const pick = (text: string) => memo.get(key(target, text)) ?? text
    return {
      ...plan,
      summary: pick(plan.summary),
      days: plan.days.map((day) => (day.note ? { ...day, note: pick(day.note) } : day)),
    }
  })

  /** True once the prose on screen is a machine translation */
  const isTranslated = computed(() => {
    void version.value
    return needed.value && texts.value.some((text) => text.trim() && memo.has(key(locale.value, text)))
  })

  return { shown, translating, failed, isTranslated }
}
