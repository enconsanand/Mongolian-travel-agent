export type AppLocale = 'mn' | 'en'

export const PREFERENCE_GROUP_IDS = ['groupSize', 'duration', 'budget', 'travelStyle'] as const
export type PreferenceGroupId = (typeof PREFERENCE_GROUP_IDS)[number]

export const PLAN_SEARCH_STEP_IDS = ['speech', 'camps', 'events'] as const
export type PlanSearchStepId = (typeof PLAN_SEARCH_STEP_IDS)[number]

export type PlanSearchStepStatus = 'pending' | 'active' | 'complete'

export interface PresetPreferenceSelection {
  kind: 'preset'
  optionId: string
}

export interface CustomPreferenceSelection {
  kind: 'custom'
  amount: number
}

export type PreferenceSelection = PresetPreferenceSelection | CustomPreferenceSelection

export type ChipPreferenceId = Exclude<PreferenceGroupId, 'duration'>

export interface TravelPeriod {
  startDate: string
  endDate: string
}

export interface TripPreferences {
  groupSize: PreferenceSelection | null
  duration: TravelPeriod
  budget: PreferenceSelection | null
  travelStyle: PreferenceSelection | null
}

export interface PreferenceOptionDefinition {
  id: string
  label: Record<AppLocale, string>
}

export interface PreferenceCustomFieldDefinition {
  placeholder: string
  unit: Record<AppLocale, string>
  ariaLabel: Record<AppLocale, string>
}

interface PreferenceGroupBase {
  icon: string
  title: Record<AppLocale, string>
}

export interface ChipPreferenceGroupDefinition extends PreferenceGroupBase {
  id: ChipPreferenceId
  kind: 'chips'
  options: PreferenceOptionDefinition[]
  customField?: PreferenceCustomFieldDefinition
}

export interface PeriodPreferenceGroupDefinition extends PreferenceGroupBase {
  id: 'duration'
  kind: 'period'
}

export type PreferenceGroupDefinition = ChipPreferenceGroupDefinition | PeriodPreferenceGroupDefinition

export interface LocalizedPreferenceOption {
  id: string
  label: string
}

export interface LocalizedPreferenceCustomField {
  placeholder: string
  unit: string
  ariaLabel: string
}

interface LocalizedPreferenceGroupBase {
  icon: string
  title: string
}

export interface LocalizedChipPreferenceGroup extends LocalizedPreferenceGroupBase {
  id: ChipPreferenceId
  kind: 'chips'
  options: LocalizedPreferenceOption[]
  customField?: LocalizedPreferenceCustomField
}

export interface LocalizedPeriodPreferenceGroup extends LocalizedPreferenceGroupBase {
  id: 'duration'
  kind: 'period'
}

export type LocalizedPreferenceGroup = LocalizedChipPreferenceGroup | LocalizedPeriodPreferenceGroup

export interface ChipPreferenceCard extends LocalizedChipPreferenceGroup {
  selection: PreferenceSelection | null
  showMissing: boolean
}

export interface PeriodPreferenceCard extends LocalizedPeriodPreferenceGroup {
  period: TravelPeriod
  showMissing: boolean
}

export type PreferenceCard = ChipPreferenceCard | PeriodPreferenceCard

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
  voiceSupport: string
  required: string
  requiredSectionLabel: string
  preferencesIncomplete: string
  periodStartLabel: string
  periodEndLabel: string
  periodInvalid: string
  customValue: string
  generate: string
  close: string
  cancel: string
  buildingTitle: string
  buildingHint: string
  dialogLabel: string
  steps: Record<PlanSearchStepId, Record<PlanSearchStepStatus, string>>
}
