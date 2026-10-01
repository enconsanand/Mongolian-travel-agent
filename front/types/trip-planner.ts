export type AppLocale = 'mn' | 'en'

export const PLAN_SEARCH_STEP_IDS = ['intent', 'places', 'stays', 'writing'] as const
export type PlanSearchStepId = (typeof PLAN_SEARCH_STEP_IDS)[number]

export type PlanSearchStepStatus = 'pending' | 'active' | 'complete'

export interface PlanSearchStepView {
  id: PlanSearchStepId
  status: PlanSearchStepStatus
  label: string
}

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
    ask: Record<'guests' | 'dates' | 'budget', string>
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
  steps: Record<PlanSearchStepId, Record<PlanSearchStepStatus, string>>
}
