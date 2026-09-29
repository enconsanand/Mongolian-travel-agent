import {
  PLAN_SEARCH_CAMPS_READY_MS,
  PLAN_SEARCH_EVENTS_READY_MS,
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

const CHIP_PREFERENCE_IDS: ChipPreferenceId[] = ['groupSize', 'budget', 'travelStyle']

function createEmptyPreferences(): TripPreferences {
  return {
    groupSize: null,
    duration: { startDate: localIsoDate(0), endDate: localIsoDate(1) },
    budget: null,
    travelStyle: null,
  }
}

function areChipPreferencesSelected(value: TripPreferences): boolean {
  return CHIP_PREFERENCE_IDS.every((id) => value[id] !== null)
}

function createInitialStepStatuses(): Record<PlanSearchStepId, PlanSearchStepStatus> {
  return {
    speech: 'complete',
    camps: 'active',
    events: 'pending',
  }
}

export function useTripPlanner() {
  const locale = ref<AppLocale>('mn')
  const tripRequest = ref('')
  const isListening = ref(false)
  const isPlanDialogOpen = ref(false)
  const preferences = ref<TripPreferences>(createEmptyPreferences())
  const showPreferenceError = ref(false)
  const stepStatuses = ref(createInitialStepStatuses())
  const stepTimers: ReturnType<typeof setTimeout>[] = []

  const messages = computed<TripPlannerMessages>(() => TRIP_PLANNER_MESSAGES[locale.value])

  const localizedGroups = computed(() => PREFERENCE_GROUPS.map((group) => localizePreferenceGroup(group, locale.value)))

  const voiceStatusLabel = computed(() => (isListening.value ? messages.value.listening : messages.value.tapToSpeak))

  const arePreferencesComplete = computed(
    () => areChipPreferencesSelected(preferences.value) && travelPeriodError(preferences.value.duration) === null
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
        showMissing: showPreferenceError.value && selection === null,
      }
    })
  )

  const preferenceErrorMessage = computed(() => {
    if (!showPreferenceError.value || arePreferencesComplete.value) return ''

    const onlyDateOrderIsWrong =
      areChipPreferencesSelected(preferences.value) && travelPeriodError(preferences.value.duration) === 'outOfOrder'

    return onlyDateOrderIsWrong ? messages.value.periodInvalid : messages.value.preferencesIncomplete
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

  function openPlanDialog() {
    if (!arePreferencesComplete.value) {
      showPreferenceError.value = true
      return
    }

    showPreferenceError.value = false
    clearStepTimers()
    stepStatuses.value = createInitialStepStatuses()
    isPlanDialogOpen.value = true

    stepTimers.push(
      setTimeout(() => {
        stepStatuses.value = { ...stepStatuses.value, camps: 'complete', events: 'active' }
      }, PLAN_SEARCH_CAMPS_READY_MS)
    )

    stepTimers.push(
      setTimeout(() => {
        stepStatuses.value = { ...stepStatuses.value, events: 'complete' }
      }, PLAN_SEARCH_EVENTS_READY_MS)
    )
  }

  function closePlanDialog() {
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
    setLocale,
    selectPresetOption,
    setCustomPreference,
    setTravelPeriod,
    toggleVoiceInput,
    openPlanDialog,
    closePlanDialog,
  }
}
