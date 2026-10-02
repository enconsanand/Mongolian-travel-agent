import { API_ENDPOINTS, ROUTES } from '~/constants'
import type { AcceptResult, PlanRequestBody, Proposal, StayChoice } from '~/types/trip-plan'
import type { AppLocale } from '~/types/trip-planner'

export type PlanErrorCode =
  | 'planner_unavailable'
  | 'proposal_not_found'
  | 'no_stays'
  | 'unavailable'
  | 'trip_locked'
  | 'error'

function errorCode(error: unknown): PlanErrorCode {
  const code = (error as { data?: { detail?: { code?: string } } })?.data?.detail?.code
  if (code === 'planner_unavailable' || code === 'proposal_not_found' || code === 'no_stays') return code
  if (code === 'trip_locked') return code
  if (code === 'unavailable') return code
  return 'error'
}

function languageHeader(locale: AppLocale, proposalId?: string): Record<string, string> {
  let claim: string | null = null
  if (import.meta.client && proposalId) {
    try {
      claim = sessionStorage.getItem(`plan-claim:${proposalId}`)
    } catch {
      /* Storage may be unavailable. */
    }
  }
  return { 'Accept-Language': locale, ...(claim ? { 'X-Plan-Token': claim } : {}) }
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
  if (data?.claim_token && import.meta.client) {
    try {
      sessionStorage.setItem(`plan-claim:${data.id}`, data.claim_token)
    } catch {
      /* Browsing still works without storage. */
    }
  }
  return data ? { proposal: data, error: null } : { proposal: null, error: errorCode(error) }
}

/** Ask the planner to change an itinerary it made; resolves to the new version or an error code */
export async function requestRevision(
  api: ReturnType<typeof useApi>,
  proposalId: string,
  change: string,
  locale: AppLocale
): Promise<{ proposal: Proposal | null; error: PlanErrorCode | null }> {
  const { data, error } = await api.post<Proposal>(
    API_ENDPOINTS.PLANNER.REVISE(proposalId),
    { change: change.trim() },
    { headers: languageHeader(locale, proposalId) }
  )
  return data ? { proposal: data, error: null } : { proposal: null, error: errorCode(error) }
}

/** One itinerary on its page: read, revise, and accept it into a held checkout */
export function useTripPlan(proposalId: string) {
  const api = useApi()
  const auth = useCookieAuth()
  const locale = useAppLocale()

  const proposal = ref<Proposal | null>(null)
  const loading = ref(true)
  const busy = ref<'revise' | 'accept' | 'edit' | 'save' | null>(null)
  const error = ref<PlanErrorCode | null>(null)
  const staysChanged = ref(false)

  const tripFits = computed(() => {
    const plan = proposal.value
    if (!plan) return true
    if (plan.fit) return plan.fit.feasible
    return !plan.days.some((day) => day.drive_time_min > 12 * 60)
  })

  const canBook = computed(() => tripFits.value && Boolean(proposal.value?.days.some((day) => day.stay)))

  async function load() {
    loading.value = true
    const { data, error: apiError } = await api.get<Proposal>(API_ENDPOINTS.PLANNER.PROPOSAL(proposalId), {
      headers: languageHeader(locale.value, proposalId),
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
    const result = await requestRevision(api, proposalId, change, locale.value)
    busy.value = null
    if (!result.proposal) {
      error.value = result.error
      return false
    }
    proposal.value = result.proposal
    return true
  }

  async function editNights(placeId: string, delta: 1 | -1): Promise<boolean> {
    if (busy.value) return false
    busy.value = 'edit'
    error.value = null
    try {
      const { data, error: apiError } = await api.post<Proposal>(
        API_ENDPOINTS.PLANNER.NIGHTS(proposalId),
        { place_id: placeId, delta },
        { headers: languageHeader(locale.value, proposalId) }
      )
      if (!data) {
        error.value = errorCode(apiError)
        return false
      }
      proposal.value = data
      return true
    } finally {
      busy.value = null
    }
  }

  async function loadStayChoices(placeId: string): Promise<StayChoice[]> {
    const { data } = await api.get<StayChoice[]>(
      `${API_ENDPOINTS.PLANNER.STAYS(proposalId)}?place_id=${encodeURIComponent(placeId)}`,
      { headers: languageHeader(locale.value, proposalId) }
    )
    return data ?? []
  }

  let stayPick = 0

  async function chooseStay(placeId: string, stayId: string): Promise<boolean> {
    const ticket = ++stayPick
    busy.value = 'edit'
    error.value = null
    try {
      const { data, error: apiError } = await api.post<Proposal>(
        API_ENDPOINTS.PLANNER.STAY(proposalId),
        { place_id: placeId, stay_id: stayId },
        { headers: languageHeader(locale.value, proposalId) }
      )
      if (ticket !== stayPick) return true
      if (!data) {
        error.value = errorCode(apiError)
        return false
      }
      proposal.value = data
      return true
    } finally {
      if (ticket === stayPick) busy.value = null
    }
  }

  async function save() {
    if (busy.value) return
    if (!auth.isAuthenticated.value) {
      await navigateTo({ path: ROUTES.LOGIN, query: { redirect: `/plan/${proposalId}?save=1` } })
      return
    }
    busy.value = 'save'
    error.value = null
    const { data, error: apiError } = await api.post<{ trip_id: string }>(
      `/me/planner/proposals/${proposalId}/save`,
      undefined,
      { headers: languageHeader(locale.value, proposalId) }
    )
    busy.value = null
    if (data) await navigateTo({ path: `/trips/${data.trip_id}`, query: { saved: '1' } })
    else error.value = errorCode(apiError)
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
        headers: languageHeader(locale.value, proposalId),
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

  return {
    locale,
    proposal,
    loading,
    busy,
    error,
    staysChanged,
    tripFits,
    canBook,
    load,
    revise,
    editNights,
    loadStayChoices,
    chooseStay,
    accept,
    save,
  }
}
