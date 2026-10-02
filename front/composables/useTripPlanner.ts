import { API_ENDPOINTS } from '~/constants'
import { TRIP_PLANNER_MESSAGES } from '~/constants/tripPlanner'
import type { Proposal } from '~/types/trip-plan'
import type { AppLocale, TripPlannerMessages } from '~/types/trip-planner'
import { isUnrelatedQuestion, readTripFacts, toPlanRequestBody, type TripFacts } from '~/utils/tripFacts'
import { requestProposal, requestRevision, type PlanErrorCode } from './useTripPlan'
import { voiceStatusText } from './useVoiceInput'

/** What the agent must ask before it may offer to plan, in this order */
const SLOTS = ['place', 'guests', 'dates', 'budget'] as const
type Slot = (typeof SLOTS)[number]

/** A short pause before the agent answers, so a reply does not appear at the same instant as the question */
const REPLY_DELAY_MS = 450

/** Agent lines are keys, so switching language rewrites the questions already on screen */
export type ChatMessage =
  | { id: number; role: 'user'; text: string }
  | { id: number; role: 'agent'; kind: 'ask'; slot: Slot; deflect: boolean }
  | { id: number; role: 'agent'; kind: 'extra'; deflect: boolean }
  | { id: number; role: 'agent'; kind: 'ready' }
  | { id: number; role: 'agent'; kind: 'aside' }
  | { id: number; role: 'agent'; kind: 'working'; phase: 'planning' | 'revising' }
  | { id: number; role: 'agent'; kind: 'plan'; revision: boolean; proposal: Proposal }
  | { id: number; role: 'agent'; kind: 'error'; code: PlanErrorCode | null }

/** A message before it gets its id (Omit over each member of the union, not the union as a whole) */
type WithoutId<M> = M extends unknown ? Omit<M, 'id'> : never
type NewChatMessage = WithoutId<ChatMessage>

/** "Nothing else" should not be sent to the planner as a travel note */
function isNoExtra(text: string): boolean {
  return /^(байхгүй|үгүй|үгүй ээ|no|nope|nothing|nothing else|none|that's all|thats all)\.?$/i.test(text.trim())
}

function isStated(facts: TripFacts, slot: Slot): boolean {
  if (slot === 'place') return facts.stated.place
  if (slot === 'guests') return facts.stated.guests
  if (slot === 'dates') return facts.stated.dates
  return facts.stated.budget
}

/** A bare answer to the agent's question ("3", "4") gets the unit the question implied */
function withUnit(text: string, slot: Slot | null, locale: AppLocale): string {
  const bare = text.trim().match(/^(?:about|around|ойролцоогоор)?\s*(\d+(?:[.,]\d+)?)\s*$/i)
  if (!bare || !slot) return text
  const amount = bare[1]!
  if (slot === 'guests') return locale === 'mn' ? `${amount} хүн` : `${amount} people`
  if (slot === 'dates') return text
  // A small number for a budget is millions ("4" = 4 million)
  if (Number(amount.replace(',', '.')) >= 1000) return `${amount}₮`
  return locale === 'mn' ? `${amount} сая` : `${amount} million`
}

/**
 * The trip planner as a conversation. The agent asks where, how many people, the date range and the budget
 * when the text leaves them out. An unrelated question is turned back to the question in hand. Once every
 * answer is in, the traveller presses the button to plan. Later messages revise that same plan.
 */
export function useTripPlanner() {
  const api = useApi()
  const locale = useState<AppLocale>('app-locale', () => 'mn')
  const messages = computed<TripPlannerMessages>(() => TRIP_PLANNER_MESSAGES[locale.value])

  const draft = ref('')
  // The microphone: Anir's transcript is added to whatever is already typed
  const voice = useVoiceInput((text) => {
    draft.value = draft.value.trim() ? `${draft.value.trim()} ${text}` : text
  })
  const isListening = computed(() => voice.state.value === 'recording')
  const chat = ref<ChatMessage[]>([])
  const busy = ref(false)
  const proposalId = ref<string | null>(null)
  /** Every required answer is in, so the chat may show the plan button */
  const canGenerate = ref(false)

  // What the traveller said before the first plan, and which question the agent is waiting on
  const brief: string[] = []
  const pendingSlot = ref<Slot | null>(null)
  /** Start a week out, and keep a length the traveller already named, until they pick real dates */
  const dateDefaults = computed(() => {
    void chat.value.length
    const facts = readTripFacts(brief.join('. '))
    return { start: facts.startDate, end: facts.endDate }
  })
  let placeNamed = false
  let extraAsked = false
  let awaitingExtra = false
  let nextId = 0
  const timers: ReturnType<typeof setTimeout>[] = []
  // Bumped on reset, so an answer to a conversation that was cleared is dropped
  let conversation = 0

  const voiceStatusLabel = computed(() => voiceStatusText(voice.state.value, messages.value, messages.value.tapToSpeak))
  const hasStarted = computed(() => chat.value.length > 0)
  /** The newest version of the plan in the conversation, for the map */
  const currentPlan = computed(() => {
    const last = chat.value.findLast((item) => item.role === 'agent' && item.kind === 'plan')
    return last?.role === 'agent' && last.kind === 'plan' ? last.proposal : null
  })

  function push(message: NewChatMessage): number {
    const id = nextId++
    chat.value.push({ ...message, id } as ChatMessage)
    return id
  }

  function replace(id: number, message: NewChatMessage) {
    const index = chat.value.findIndex((item) => item.id === id)
    if (index >= 0) chat.value[index] = { ...message, id } as ChatMessage
  }

  function later(run: () => void, delay: number) {
    timers.push(setTimeout(run, delay))
  }

  function clearTimers() {
    timers.forEach((timer) => clearTimeout(timer))
    timers.length = 0
  }

  /** Shows one waiting line while ``run`` asks the planner, then its answer in that line's place */
  async function work(
    phase: 'planning' | 'revising',
    run: () => Promise<{ proposal: Proposal | null; error: PlanErrorCode | null }>
  ) {
    const seq = conversation
    busy.value = true
    const workingId = push({ role: 'agent', kind: 'working', phase })

    const { proposal, error } = await run()
    if (seq !== conversation) return
    clearTimers()
    busy.value = false

    if (!proposal) {
      canGenerate.value = proposalId.value === null
      replace(workingId, { role: 'agent', kind: 'error', code: error })
      return
    }
    const isRevision = proposalId.value !== null
    proposalId.value = proposal.id
    replace(workingId, { role: 'agent', kind: 'plan', revision: isRevision, proposal })
  }

  function plan() {
    canGenerate.value = false
    const text = brief.join('. ')
    const facts = readTripFacts(text)
    work('planning', () => requestProposal(api, toPlanRequestBody(facts, text), locale.value))
  }

  function revise(change: string) {
    const id = proposalId.value!
    work('revising', () => requestRevision(api, id, change, locale.value))
  }

  function factsNow(): TripFacts {
    return readTripFacts(brief.join('. '))
  }

  function slotDone(facts: TripFacts, slot: Slot): boolean {
    if (slot === 'place') return facts.stated.place || placeNamed
    return isStated(facts, slot)
  }

  function nextSlot(facts: TripFacts): Slot | null {
    return SLOTS.find((slot) => !slotDone(facts, slot)) ?? null
  }

  /** The reply fills the question the agent just asked, even as a bare number */
  function answersSlot(text: string, slot: Slot): boolean {
    const facts = readTripFacts(withUnit(text, slot, locale.value))
    if (slot === 'place') return facts.stated.place || (!isUnrelatedQuestion(text) && /\p{L}{2,}/u.test(text))
    return isStated(facts, slot)
  }

  function reply(message: NewChatMessage) {
    const seq = conversation
    busy.value = true
    later(() => {
      if (seq !== conversation) return
      busy.value = false
      push(message)
    }, REPLY_DELAY_MS)
  }

  function offer() {
    awaitingExtra = false
    pendingSlot.value = null
    canGenerate.value = true
    if (chat.value.some((item) => item.role === 'agent' && item.kind === 'ready')) return
    reply({ role: 'agent', kind: 'ready' })
  }

  /** Ask the next missing question, then whether anything else should be added, then the plan button */
  function advance() {
    const missing = nextSlot(factsNow())
    if (missing) {
      awaitingExtra = false
      pendingSlot.value = missing
      reply({ role: 'agent', kind: 'ask', slot: missing, deflect: false })
      return
    }
    if (!extraAsked) {
      extraAsked = true
      awaitingExtra = true
      pendingSlot.value = null
      reply({ role: 'agent', kind: 'extra', deflect: false })
      return
    }
    offer()
  }

  function submit(text: string) {
    if (!text || busy.value) return
    push({ role: 'user', text })

    if (proposalId.value) {
      revise(text)
      return
    }

    if (awaitingExtra) {
      if (isNoExtra(text)) {
        offer()
        return
      }
      if (isUnrelatedQuestion(text)) {
        reply({ role: 'agent', kind: 'extra', deflect: true })
        return
      }
      brief.push(text)
      offer()
      return
    }

    const slot = pendingSlot.value
    // A question that does not answer the one in hand is turned back to that question
    if (isUnrelatedQuestion(text) && !(slot && answersSlot(text, slot))) {
      if (slot) reply({ role: 'agent', kind: 'ask', slot, deflect: true })
      else if (!canGenerate.value) {
        pendingSlot.value = 'place'
        reply({ role: 'agent', kind: 'ask', slot: 'place', deflect: true })
      } else reply({ role: 'agent', kind: 'aside' })
      return
    }

    if (slot && !answersSlot(text, slot)) {
      void clarify(slot, text)
      return
    }

    brief.push(withUnit(text, slot, locale.value))
    if (slot === 'place') placeNamed = true
    advance()
  }

  /** The form did not read this reply: ask the planner model, then accept it or ask again */
  async function clarify(slot: Slot, text: string) {
    const seq = conversation
    busy.value = true
    const { data } = await api.post<{ understood: boolean; normalized: string }>(API_ENDPOINTS.PLANNER.READ, {
      slot,
      text,
    })
    if (seq !== conversation) return
    busy.value = false
    const normalized = data?.understood ? data.normalized.trim() : ''
    if (normalized && answersSlot(normalized, slot)) {
      brief.push(withUnit(normalized, slot, locale.value))
      if (slot === 'place') placeNamed = true
      advance()
      return
    }
    reply({ role: 'agent', kind: 'ask', slot, deflect: false })
  }

  function send() {
    const text = draft.value.trim()
    if (!text || busy.value) return
    draft.value = ''
    submit(text)
  }

  /** A chip or the date picker answers the question in hand */
  function pick(text: string) {
    submit(text.trim())
  }

  function generate() {
    if (busy.value || !canGenerate.value || proposalId.value) return
    plan()
  }

  /** The last plan request failed: try it again as it was */
  function retry() {
    if (busy.value) return
    chat.value = chat.value.filter((item) => !(item.role === 'agent' && item.kind === 'error'))
    if (proposalId.value) {
      const lastUser = [...chat.value].reverse().find((item) => item.role === 'user')
      if (lastUser) revise(lastUser.text)
      return
    }
    plan()
  }

  function reset() {
    conversation++
    clearTimers()
    chat.value = []
    draft.value = ''
    busy.value = false
    proposalId.value = null
    canGenerate.value = false
    brief.length = 0
    pendingSlot.value = null
    placeNamed = false
    extraAsked = false
    awaitingExtra = false
  }

  function setLocale(nextLocale: AppLocale) {
    locale.value = nextLocale
  }

  function toggleVoiceInput() {
    voice.toggle()
  }

  onScopeDispose(clearTimers)

  return {
    locale,
    messages,
    draft,
    chat,
    busy,
    hasStarted,
    currentPlan,
    isListening,
    voiceStatusLabel,
    setLocale,
    toggleVoiceInput,
    canGenerate,
    pendingSlot,
    dateDefaults,
    send,
    pick,
    generate,
    retry,
    reset,
  }
}
