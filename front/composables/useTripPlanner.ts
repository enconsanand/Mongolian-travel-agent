import {
  PLAN_STEP_STARTS_MS,
  PREFERENCE_GROUPS,
  TRIP_PLANNER_MESSAGES,
  localizePreferenceGroup,
} from '~/constants/tripPlanner'
import { PLAN_SEARCH_STEP_IDS } from '~/types/trip-planner'
import type {
  AppLocale,
  ChipPreferenceId,
  PlanSearchStepId,
  PlanSearchStepStatus,
  PlanSearchStepView,
  PreferenceCard,
  TravelPeriod,
  TripPlannerMessages,
  TripPreferences,
} from '~/types/trip-planner'
import { localIsoDate, travelPeriodError } from '~/utils/dates'
import { toPlanRequestBody } from '~/utils/tripPlan'
import { requestProposal } from './useTripPlan'

const CHIP_PREFERENCE_IDS: ChipPreferenceId[] = ['groupSize', 'budget', 'travelStyle']

function createEmptyPreferences(): TripPreferences {
  return {
    groupSize: null,
    duration: { startDate: localIsoDate(0), endDate: localIsoDate(1) },
    budget: null,
    travelStyle: null,
  }
}

/** The planner's limit (PlanRequest.guests in back/app/modules/orchestrator/types.py) */
const MAX_GUESTS = 60

function areChipPreferencesSelected(value: TripPreferences): boolean {
  return CHIP_PREFERENCE_IDS.every((id) => value[id] !== null)
}

function isGroupTooLarge(value: TripPreferences): boolean {
  return value.groupSize?.kind === 'custom' && Math.round(value.groupSize.amount) > MAX_GUESTS
}

function createInitialStepStatuses(): Record<PlanSearchStepId, PlanSearchStepStatus> {
  return { intent: 'active', places: 'pending', stays: 'pending', writing: 'pending' }
}

/** Steps before ``stepId`` complete, ``stepId`` active, the rest pending */
function statusesFrom(stepId: PlanSearchStepId): Record<PlanSearchStepId, PlanSearchStepStatus> {
  const at = PLAN_SEARCH_STEP_IDS.indexOf(stepId)
  return Object.fromEntries(
    PLAN_SEARCH_STEP_IDS.map((id, i) => [id, i < at ? 'complete' : i === at ? 'active' : 'pending'])
  ) as Record<PlanSearchStepId, PlanSearchStepStatus>
}

export function useTripPlanner() {
  const api = useApi()
  const locale = useState<AppLocale>('app-locale', () => 'mn')
  const tripRequest = ref('')
  const isListening = ref(false)
  const isPlanDialogOpen = ref(false)
  const preferences = ref<TripPreferences>(createEmptyPreferences())
  const showPreferenceError = ref(false)
  const stepStatuses = ref(createInitialStepStatuses())
  const planError = ref<'planner_unavailable' | 'error' | null>(null)
  const stepTimers: ReturnType<typeof setTimeout>[] = []
  // Bumped on every request and on close, so a late answer to a cancelled request is ignored
  let requestSeq = 0

  const messages = computed<TripPlannerMessages>(() => TRIP_PLANNER_MESSAGES[locale.value])

  const localizedGroups = computed(() => PREFERENCE_GROUPS.map((group) => localizePreferenceGroup(group, locale.value)))

  const voiceStatusLabel = computed(() => (isListening.value ? messages.value.listening : messages.value.tapToSpeak))

  const arePreferencesComplete = computed(
    () =>
      areChipPreferencesSelected(preferences.value) &&
      !isGroupTooLarge(preferences.value) &&
      travelPeriodError(preferences.value.duration) === null
  )

  const preferenceCards = computed<PreferenceCard[]>(() =>
    localizedGroups.value.map((group) => {
      if (group.kind === 'period') {
        return {
          ...group,
          period: preferences.value.duration,
          showMissing: showPreferenceError.value && travelPeriodError(preferences.value.duration) !== null,
        }
      }

      const selection = preferences.value[group.id]
      return {
        ...group,
        selection,
        showMissing:
          showPreferenceError.value &&
          (selection === null || (group.id === 'groupSize' && isGroupTooLarge(preferences.value))),
      }
    })
  )

  const preferenceErrorMessage = computed(() => {
    if (!showPreferenceError.value || arePreferencesComplete.value) return ''

    if (!areChipPreferencesSelected(preferences.value)) return messages.value.preferencesIncomplete
    if (isGroupTooLarge(preferences.value)) return messages.value.groupTooLarge

    const periodError = travelPeriodError(preferences.value.duration)
    if (periodError === 'outOfOrder') return messages.value.periodInvalid
    if (periodError === 'tooLong') return messages.value.periodTooLong
    return messages.value.preferencesIncomplete
  })

  const planSearchSteps = computed<PlanSearchStepView[]>(() =>
    PLAN_SEARCH_STEP_IDS.map((stepId) => ({
      id: stepId,
      status: stepStatuses.value[stepId],
      label: messages.value.steps[stepId][stepStatuses.value[stepId]],
    }))
  )

  function setLocale(nextLocale: AppLocale) {
    locale.value = nextLocale
  }

  function selectPresetOption(groupId: ChipPreferenceId, optionId: string) {
    preferences.value = {
      ...preferences.value,
      [groupId]: { kind: 'preset', optionId },
    }
  }

  function setCustomPreference(groupId: ChipPreferenceId, rawValue: string) {
    const amount = Number(rawValue)
    const hasAmount = rawValue.trim() !== '' && Number.isFinite(amount) && amount > 0

    preferences.value = {
      ...preferences.value,
      [groupId]: hasAmount ? { kind: 'custom', amount } : null,
    }
  }

  function setTravelPeriod(field: keyof TravelPeriod, value: string) {
    preferences.value = {
      ...preferences.value,
      duration: { ...preferences.value.duration, [field]: value },
    }
  }

  function toggleVoiceInput() {
    isListening.value = !isListening.value
  }

  function clearStepTimers() {
    stepTimers.forEach((timerId) => clearTimeout(timerId))
    stepTimers.length = 0
  }

  async function openPlanDialog() {
    if (!arePreferencesComplete.value) {
      showPreferenceError.value = true
      return
    }

    showPreferenceError.value = false
    clearStepTimers()
    stepStatuses.value = createInitialStepStatuses()
    planError.value = null
    isPlanDialogOpen.value = true
    const seq = ++requestSeq

    for (const [stepId, delay] of Object.entries(PLAN_STEP_STARTS_MS) as [PlanSearchStepId, number][]) {
      stepTimers.push(setTimeout(() => (stepStatuses.value = statusesFrom(stepId)), delay))
    }

    const { proposal, error } = await requestProposal(
      api,
      toPlanRequestBody(preferences.value, tripRequest.value),
      locale.value
    )
    if (seq !== requestSeq) return
    clearStepTimers()

    if (!proposal) {
      planError.value = error === 'planner_unavailable' ? 'planner_unavailable' : 'error'
      return
    }
    stepStatuses.value = { intent: 'complete', places: 'complete', stays: 'complete', writing: 'complete' }
    isPlanDialogOpen.value = false
    await navigateTo(`/plan/${proposal.id}`)
  }

  function closePlanDialog() {
    requestSeq++
    clearStepTimers()
    isPlanDialogOpen.value = false
  }

  watch(arePreferencesComplete, (complete) => {
    if (complete) showPreferenceError.value = false
  })

  onScopeDispose(clearStepTimers)

  return {
    locale,
    messages,
    tripRequest,
    isListening,
    isPlanDialogOpen,
    preferenceErrorMessage,
    preferenceCards,
    voiceStatusLabel,
    planSearchSteps,
    planError,
    setLocale,
    selectPresetOption,
    setCustomPreference,
    setTravelPeriod,
    toggleVoiceInput,
    openPlanDialog,
    closePlanDialog,
  }
}
