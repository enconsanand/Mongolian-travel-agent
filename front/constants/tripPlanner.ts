import type {
  AppLocale,
  LocalizedPreferenceGroup,
  PreferenceGroupDefinition,
  TripPlannerMessages,
} from '~/types/trip-planner'

export const PLAN_SEARCH_CAMPS_READY_MS = 2500
export const PLAN_SEARCH_EVENTS_READY_MS = 5000

export const VOICE_METER_DELAYS_MS = [0, 150, 300, 450, 200] as const

export const TRIP_PLANNER_MESSAGES: Record<AppLocale, TripPlannerMessages> = {
  mn: {
    documentTitle: 'Mongolian Travel AI Agent',
    languageGroupLabel: 'Хэл',
    heroTitle: 'Монгол аялалдаа бэлэн үү?',
    heroSubtitle: 'Аяллын сонирхол, хүсэлтээ бичих эсвэл ярьж оруулна уу.',
    requestLabel: 'Аяллын хүсэлт',
    requestPlaceholder: 'Жишээ: Морь унах, шөнө одод харах боломжтой газар луу аялмаар байна...',
    tapToSpeak: 'Дуугаар оруулах',
    listening: 'Сонсож байна… зогсоохын тулд дахин дарна уу',
    voiceButtonLabel: 'Монгол хэлээр дуут оруулалт',
    voiceSupport: 'Монгол яриаг автоматаар текст болгоно (Anir STT)',
    required: 'Заавал',
    requiredSectionLabel: 'Заавал сонгох',
    preferencesIncomplete: 'Хүний тоо, аялах хугацаа, төсөв, хэв маягийг сонгоно уу.',
    periodStartLabel: 'Эхлэх өдөр',
    periodEndLabel: 'Дуусах өдөр',
    periodInvalid: 'Дуусах өдөр эхлэх өдрөөс хойш байх ёстой.',
    customValue: 'Өөр утга',
    generate: 'Аяллын хөтөлбөр үүсгэх',
    close: 'Хаах',
    cancel: 'Хаах',
    buildingTitle: 'Аяллын хөтөлбөр бэлдэж байна...',
    buildingHint: 'Ихэвчлэн 10–20 секунд болно',
    dialogLabel: 'Төлөвлөгөө үүсгэх явц',
    steps: {
      speech: {
        pending: 'Anir STT: яриа ба текстийг задлах',
        active: 'Anir STT: яриа ба текстийг задалж байна...',
        complete: 'Anir STT: яриа ба текстийг задаллаа',
      },
      camps: {
        pending: 'MongoDB: гэр баазын сул өрөө хайх',
        active: 'MongoDB: гэр баазын сул өрөө хайж байна...',
        complete: 'MongoDB: гэр баазын сул өрөө олдлоо',
      },
      events: {
        pending: 'Cultural events: Наадмын арга хэмжээ хайх...',
        active: 'Cultural events: Наадмын арга хэмжээ хайж байна...',
        complete: 'Cultural events: Наадмын арга хэмжээ олдлоо',
      },
    },
  },
  en: {
    documentTitle: 'Mongolian Travel AI Agent',
    languageGroupLabel: 'Language',
    heroTitle: 'Design your Mongolia trip, instantly.',
    heroSubtitle: 'Type or speak your ideal travel preferences and activities.',
    requestLabel: 'Trip request',
    requestPlaceholder: 'e.g. I want to ride horses, stay in a ger camp, and gaze at starry night skies...',
    tapToSpeak: 'Tap to Speak',
    listening: 'Listening… tap again to stop',
    voiceButtonLabel: 'Tap to Speak',
    voiceSupport: 'Mongolian Voice Input Supported (Anir STT)',
    required: 'Required',
    requiredSectionLabel: 'Required selections',
    preferencesIncomplete: 'Choose a group size, travel dates, budget, and style.',
    periodStartLabel: 'Start date',
    periodEndLabel: 'End date',
    periodInvalid: 'The end date must be on or after the start date.',
    customValue: 'Custom',
    generate: 'Generate My Itinerary',
    close: 'Close',
    cancel: 'Cancel',
    buildingTitle: 'Creating Your Itinerary...',
    buildingHint: 'This usually takes 10–20 seconds',
    dialogLabel: 'Itinerary creation progress',
    steps: {
      speech: {
        pending: 'Parsing your travel request (Anir STT)...',
        active: 'Parsing your travel request (Anir STT)...',
        complete: 'Travel request parsed (Anir STT)',
      },
      camps: {
        pending: 'Searching available Ger Camps (MongoDB)...',
        active: 'Searching available Ger Camps (MongoDB)...',
        complete: 'Available ger camps found (MongoDB)',
      },
      events: {
        pending: 'Matching local cultural events & Naadam...',
        active: 'Matching local cultural events & Naadam...',
        complete: 'Local cultural events & Naadam matched',
      },
    },
  },
}

export const PREFERENCE_GROUPS: PreferenceGroupDefinition[] = [
  {
    id: 'groupSize',
    kind: 'chips',
    icon: 'pi pi-users',
    title: { mn: 'Хүний тоо', en: 'Group size' },
    options: [
      { id: '1', label: { mn: '1 хүн', en: '1 person' } },
      { id: '2', label: { mn: '2 хүн', en: '2 people' } },
      { id: '4', label: { mn: '4 хүн', en: '4 people' } },
    ],
    customField: {
      placeholder: '5',
      unit: { mn: 'хүн', en: 'people' },
      ariaLabel: { mn: 'Хүний тоог өөрөө оруулах', en: 'Enter a custom group size' },
    },
  },
  {
    id: 'duration',
    kind: 'period',
    icon: 'pi pi-calendar',
    title: { mn: 'Аялах хугацаа', en: 'Travel dates' },
  },
  {
    id: 'budget',
    kind: 'chips',
    icon: 'pi pi-wallet',
    title: { mn: 'Нийт төсөв', en: 'Total budget' },
    options: [
      { id: 'up-to-2m', label: { mn: '2 сая₮ хүртэл', en: 'Up to 2M MNT' } },
      { id: 'up-to-3-5m', label: { mn: '3.5 сая₮ хүртэл', en: 'Up to 3.5M MNT' } },
      { id: 'up-to-5m', label: { mn: '5 сая₮ хүртэл', en: 'Up to 5M MNT' } },
      { id: 'unlimited', label: { mn: 'Хязгааргүй', en: 'No limit' } },
    ],
    customField: {
      placeholder: '4',
      unit: { mn: 'сая₮', en: 'MNT' },
      ariaLabel: { mn: 'Нийт төсвийг өөрөө оруулах', en: 'Enter a custom total budget' },
    },
  },
  {
    id: 'travelStyle',
    kind: 'chips',
    icon: 'pi pi-map',
    title: { mn: 'Аяллын хэв маяг', en: 'Style' },
    options: [
      { id: 'value', label: { mn: 'Хэмнэлттэй', en: 'Budget-friendly' } },
      { id: 'comfort', label: { mn: 'VIP / Тав тухтай', en: 'Luxury / Glamping' } },
      { id: 'culture', label: { mn: 'Наадам ба соёл', en: 'Culture & Naadam' } },
    ],
  },
]

export function localizePreferenceGroup(group: PreferenceGroupDefinition, locale: AppLocale): LocalizedPreferenceGroup {
  const shared = {
    icon: group.icon,
    title: group.title[locale],
  }

  if (group.kind === 'period') {
    return { ...shared, id: group.id, kind: 'period' }
  }

  return {
    ...shared,
    id: group.id,
    kind: 'chips',
    options: group.options.map((option) => ({
      id: option.id,
      label: option.label[locale],
    })),
    customField: group.customField
      ? {
          placeholder: group.customField.placeholder,
          unit: group.customField.unit[locale],
          ariaLabel: group.customField.ariaLabel[locale],
        }
      : undefined,
  }
}
