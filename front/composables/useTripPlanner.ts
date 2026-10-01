import { PLAN_STEP_STARTS_MS, TRIP_PLANNER_MESSAGES } from '~/constants/tripPlanner'
import type { Proposal } from '~/types/trip-plan'
import { PLAN_SEARCH_STEP_IDS } from '~/types/trip-planner'
import type {
  AppLocale,
  PlanSearchStepId,
  PlanSearchStepStatus,
  PlanSearchStepView,
  TripPlannerMessages,
} from '~/types/trip-planner'
import { readTripFacts, toPlanRequestBody, type TripFacts } from '~/utils/tripFacts'
import { requestProposal, requestRevision, type PlanErrorCode } from './useTripPlan'

/** What the agent asks for before it plans, in this order, unless the traveller already said it */
const SLOTS = ['guests', 'dates', 'budget'] as const
type Slot = (typeof SLOTS)[number]

/** A short pause before the agent answers, so a reply does not appear at the same instant as the question */
const REPLY_DELAY_MS = 450

export type ChatMessage =
  | { id: number; role: 'user'; text: string }
  | { id: number; role: 'agent'; kind: 'text'; text: string }
  | { id: number; role: 'agent'; kind: 'working'; text: string; steps: PlanSearchStepView[] }
  | { id: number; role: 'agent'; kind: 'plan'; text: string; proposal: Proposal }
  | { id: number; role: 'agent'; kind: 'error'; text: string }

/** A message before it gets its id (Omit over each member of the union, not the union as a whole) */
type WithoutId<M> = M extends unknown ? Omit<M, 'id'> : never
type NewChatMessage = WithoutId<ChatMessage>

function isStated(facts: TripFacts, slot: Slot): boolean {
  if (slot === 'guests') return facts.stated.guests
  if (slot === 'dates') return facts.stated.dates || facts.stated.days
  return facts.stated.budget
}

/** A bare answer to the agent's question ("3", "4") gets the unit the question implied */
function withUnit(text: string, slot: Slot | null, locale: AppLocale): string {
  const bare = text.trim().match(/^(?:about|around|ойролцоогоор)?\s*(\d+(?:[.,]\d+)?)\s*$/i)
  if (!bare || !slot) return text
  const amount = bare[1]!
  if (slot === 'guests') return locale === 'mn' ? `${amount} хүн` : `${amount} people`
  if (slot === 'dates') return locale === 'mn' ? `${amount} хоног` : `${amount} days`
  // A small number for a budget is millions ("4" = 4 million)
  return Number(amount.replace(',', '.')) < 1000 ? `${amount} сая` : `${amount}₮`
}

function stepViews(
  statuses: Record<PlanSearchStepId, PlanSearchStepStatus>,
  messages: TripPlannerMessages
): PlanSearchStepView[] {
  return PLAN_SEARCH_STEP_IDS.map((id) => ({ id, status: statuses[id], label: messages.steps[id][statuses[id]] }))
}

/** Steps before ``stepId`` complete, ``stepId`` active, the rest pending */
function statusesFrom(stepId: PlanSearchStepId): Record<PlanSearchStepId, PlanSearchStepStatus> {
  const at = PLAN_SEARCH_STEP_IDS.indexOf(stepId)
  return Object.fromEntries(
    PLAN_SEARCH_STEP_IDS.map((id, i) => [id, i < at ? 'complete' : i === at ? 'active' : 'pending'])
  ) as Record<PlanSearchStepId, PlanSearchStepStatus>
}

/**
 * The trip planner as a conversation. The traveller writes what they want; the agent asks for the group size,
 * dates and budget when the text leaves them out, then plans. Every later message revises that same plan.
 */
export function useTripPlanner() {
  const api = useApi()
  const locale = useState<AppLocale>('app-locale', () => 'mn')
  const messages = computed<TripPlannerMessages>(() => TRIP_PLANNER_MESSAGES[locale.value])

  const draft = ref('')
  const isListening = ref(false)
  const chat = ref<ChatMessage[]>([])
  const busy = ref(false)
  const proposalId = ref<string | null>(null)

  // What the traveller said before the first plan, and which questions the agent already asked
  const brief: string[] = []
  const asked = new Set<Slot>()
  let pendingSlot: Slot | null = null
  let nextId = 0
  const timers: ReturnType<typeof setTimeout>[] = []
  // Bumped on reset, so an answer to a conversation that was cleared is dropped
  let conversation = 0

  const voiceStatusLabel = computed(() => (isListening.value ? messages.value.listening : messages.value.tapToSpeak))
  const hasStarted = computed(() => chat.value.length > 0)

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

  function errorText(code: PlanErrorCode | null): string {
    return code === 'planner_unavailable' ? messages.value.errors.planner_unavailable : messages.value.errors.error
  }

  /** Shows the planning steps while ``run`` waits on the planner, then its answer in their place */
  async function work(intro: string, run: () => Promise<{ proposal: Proposal | null; error: PlanErrorCode | null }>) {
    const seq = conversation
    busy.value = true
    const workingId = push({
      role: 'agent',
      kind: 'working',
      text: intro,
      steps: stepViews(statusesFrom('intent'), messages.value),
    })
    for (const [stepId, delay] of Object.entries(PLAN_STEP_STARTS_MS) as [PlanSearchStepId, number][]) {
      later(() => {
        const current = chat.value.find((item) => item.id === workingId)
        if (current?.role === 'agent' && current.kind === 'working') {
          replace(workingId, { ...current, steps: stepViews(statusesFrom(stepId), messages.value) })
        }
      }, delay)
    }

    const { proposal, error } = await run()
    if (seq !== conversation) return
    clearTimers()
    busy.value = false

    if (!proposal) {
      replace(workingId, { role: 'agent', kind: 'error', text: errorText(error) })
      return
    }
    const isRevision = proposalId.value !== null
    proposalId.value = proposal.id
    replace(workingId, {
      role: 'agent',
      kind: 'plan',
      text: isRevision ? messages.value.chat.revised : messages.value.chat.planned,
      proposal,
    })
  }

  function plan() {
    const text = brief.join('. ')
    const facts = readTripFacts(text)
    work(messages.value.chat.planning, () => requestProposal(api, toPlanRequestBody(facts, text), locale.value))
  }

  function revise(change: string) {
    const id = proposalId.value!
    work(messages.value.chat.revising, () => requestRevision(api, id, change, locale.value))
  }

  /** The agent's next move before the first plan: ask what is still missing, or plan */
  function answer() {
    const facts = readTripFacts(brief.join('. '))
    const missing = SLOTS.find((slot) => !isStated(facts, slot) && !asked.has(slot))
    if (!missing) {
      pendingSlot = null
      plan()
      return
    }
    pendingSlot = missing
    asked.add(missing)
    const seq = conversation
    busy.value = true
    later(() => {
      if (seq !== conversation) return
      busy.value = false
      push({ role: 'agent', kind: 'text', text: messages.value.chat.ask[missing] })
    }, REPLY_DELAY_MS)
  }

  function send() {
    const text = draft.value.trim()
    if (!text || busy.value) return
    draft.value = ''
    isListening.value = false
    push({ role: 'user', text })

    if (proposalId.value) {
      revise(text)
      return
    }
    brief.push(withUnit(text, pendingSlot, locale.value))
    answer()
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
    brief.length = 0
    asked.clear()
    pendingSlot = null
  }

  function setLocale(nextLocale: AppLocale) {
    locale.value = nextLocale
  }

  function toggleVoiceInput() {
    isListening.value = !isListening.value
  }

  onScopeDispose(clearTimers)

  return {
    locale,
    messages,
    draft,
    chat,
    busy,
    hasStarted,
    isListening,
    voiceStatusLabel,
    setLocale,
    toggleVoiceInput,
    send,
    retry,
    reset,
  }
}
