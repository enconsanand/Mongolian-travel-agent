export type AppLocale = 'mn' | 'en'

export interface TripPlannerMessages {
  documentTitle: string
  languageGroupLabel: string
  heroTitle: string
  heroSubtitle: string
  requestLabel: string
  requestPlaceholder: string
  tapToSpeak: string
  listening: string
  voiceButtonLabel: string
  generate: string
  retry: string
  chat: {
    ask: Record<'place' | 'guests' | 'dates' | 'budget', string>
    choices: {
      fromDate: string
      toDate: string
      useDates: string
      datesInvalid: string
      guestSuffix: string
      guests: number[]
      budgets: { label: string; value: string }[]
      places: { label: string; value: string }[]
    }
    extra: string
    noExtra: string
    offTopic: string
    offTopicReady: string
    ready: string
    generatePlan: string
    planning: string
    revising: string
    planned: string
    revised: string
    agentName: string
    replyPlaceholder: string
    newTrip: string
    openPlan: string
    days: string
    total: string
  }
  errors: Record<'planner_unavailable' | 'error', string>
}
