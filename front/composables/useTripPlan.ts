import { API_ENDPOINTS, ROUTES } from '~/constants'
import type { AcceptResult, PlanRequestBody, Proposal } from '~/types/trip-plan'
import type { AppLocale } from '~/types/trip-planner'

export type PlanErrorCode = 'planner_unavailable' | 'proposal_not_found' | 'no_stays' | 'unavailable' | 'error'

function errorCode(error: unknown): PlanErrorCode {
  const code = (error as { data?: { detail?: { code?: string } } })?.data?.detail?.code
  if (code === 'planner_unavailable' || code === 'proposal_not_found' || code === 'no_stays') return code
  if (code === 'unavailable') return code
  return 'error'
}

function languageHeader(locale: AppLocale) {
  return { 'Accept-Language': locale }
}

/** Ask the planner for a new itinerary; resolves to the proposal or an error code */
export async function requestProposal(
  api: ReturnType<typeof useApi>,
  body: PlanRequestBody,
  locale: AppLocale
): Promise<{ proposal: Proposal | null; error: PlanErrorCode | null }> {
  const { data, error } = await api.post<Proposal>(API_ENDPOINTS.PLANNER.PROPOSALS, body, {
    headers: languageHeader(locale),
  })
  return data ? { proposal: data, error: null } : { proposal: null, error: errorCode(error) }
}

/** One itinerary on its page: read, revise, and accept it into a held checkout */
export function useTripPlan(proposalId: string) {
  const api = useApi()
  const auth = useCookieAuth()
  const locale = useState<AppLocale>('app-locale', () => 'mn')

  const proposal = ref<Proposal | null>(null)
  const loading = ref(true)
  const busy = ref<'revise' | 'accept' | null>(null)
  const error = ref<PlanErrorCode | null>(null)
  const staysChanged = ref(false)

  const canBook = computed(() => Boolean(proposal.value?.days.some((day) => day.stay)))

  async function load() {
    loading.value = true
    const { data, error: apiError } = await api.get<Proposal>(API_ENDPOINTS.PLANNER.PROPOSAL(proposalId), {
      headers: languageHeader(locale.value),
    })
    proposal.value = data
    error.value = data ? null : errorCode(apiError) === 'error' ? 'proposal_not_found' : errorCode(apiError)
    loading.value = false
  }

  async function revise(change: string): Promise<boolean> {
    if (!change.trim() || busy.value) return false
    busy.value = 'revise'
    error.value = null
    staysChanged.value = false
    const { data, error: apiError } = await api.post<Proposal>(
      API_ENDPOINTS.PLANNER.REVISE(proposalId),
      { change: change.trim() },
      { headers: languageHeader(locale.value) }
    )
    busy.value = null
    if (!data) {
      error.value = errorCode(apiError)
      return false
    }
    proposal.value = data
    return true
  }

  async function accept() {
    if (busy.value) return
    if (!auth.isAuthenticated.value) {
      await navigateTo({ path: ROUTES.LOGIN, query: { redirect: `/plan/${proposalId}` } })
      return
    }
    busy.value = 'accept'
    error.value = null
    staysChanged.value = false
    const { data, error: apiError } = await api.post<AcceptResult>(
      API_ENDPOINTS.PLANNER.ACCEPT(proposalId),
      undefined,
      {
        headers: languageHeader(locale.value),
      }
    )
    busy.value = null
    if (data) {
      await navigateTo(`/checkout/${data.checkout_id}`)
      return
    }
    const code = errorCode(apiError)
    const replanned = (apiError as { data?: { detail?: { proposal?: Proposal } } })?.data?.detail?.proposal
    if (code === 'unavailable' && replanned) {
      proposal.value = replanned
      staysChanged.value = true
      return
    }
    error.value = code
  }

  // The catalog's names come back in the caller's language
  watch(locale, () => {
    if (proposal.value) load()
  })

  return { locale, proposal, loading, busy, error, staysChanged, canBook, load, revise, accept }
}
