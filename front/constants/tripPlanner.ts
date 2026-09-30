import type {
  AppLocale,
  LocalizedPreferenceGroup,
  PreferenceGroupDefinition,
  TripPlannerMessages,
} from '~/types/trip-planner'

/** When each planning step is shown as started while the request runs (the server does them in this order) */
export const PLAN_STEP_STARTS_MS = { places: 2500, stays: 5000, writing: 8000 } as const

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
    periodTooLong: 'Аялал хамгийн ихдээ 30 хоног байна.',
    groupTooLarge: 'Хүний тоо хамгийн ихдээ 60 байна.',
    customValue: 'Өөр утга',
    generate: 'Аяллын хөтөлбөр үүсгэх',
    close: 'Хаах',
    cancel: 'Хаах',
    buildingTitle: 'Аяллын хөтөлбөр бэлдэж байна...',
    buildingHint: 'Ихэвчлэн 10–30 секунд болно',
    dialogLabel: 'Төлөвлөгөө үүсгэх явц',
    retry: 'Дахин оролдох',
    errors: {
      planner_unavailable: 'AI төлөвлөгч түр ажиллахгүй байна. Хэсэг хүлээгээд дахин оролдоно уу.',
      error: 'Хөтөлбөр үүсгэж чадсангүй. Дахин оролдоно уу.',
    },
    steps: {
      intent: {
        pending: 'Workers AI: хүсэлтийг ойлгох',
        active: 'Workers AI: хүсэлтийг ойлгож байна...',
        complete: 'Workers AI: хүсэлтийг ойлголоо',
      },
      places: {
        pending: 'Очих газруудыг тодорхойлох',
        active: 'Очих газруудыг тодорхойлж, маршрут гаргаж байна...',
        complete: 'Маршрут бэлэн',
      },
      stays: {
        pending: 'Гэр бааз, буудлын сул өрөө, арга хэмжээ хайх',
        active: 'Гэр бааз, буудлын сул өрөө, арга хэмжээ хайж байна...',
        complete: 'Буудал, арга хэмжээ олдлоо',
      },
      writing: {
        pending: 'Хөтөлбөрийн тайлбар бичих',
        active: 'Хөтөлбөрийн тайлбар бичиж байна...',
        complete: 'Хөтөлбөр бэлэн',
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
    periodTooLong: 'A trip can be at most 30 days.',
    groupTooLarge: 'A group can be at most 60 people.',
    customValue: 'Custom',
    generate: 'Generate My Itinerary',
    close: 'Close',
    cancel: 'Cancel',
    buildingTitle: 'Creating Your Itinerary...',
    buildingHint: 'This usually takes 10–30 seconds',
    dialogLabel: 'Itinerary creation progress',
    retry: 'Try again',
    errors: {
      planner_unavailable: 'The AI planner is unavailable right now. Please try again in a moment.',
      error: 'Could not create the itinerary. Please try again.',
    },
    steps: {
      intent: {
        pending: 'Workers AI: understand your request',
        active: 'Workers AI: understanding your request...',
        complete: 'Workers AI: request understood',
      },
      places: {
        pending: 'Find the places and the route',
        active: 'Finding the places and the route...',
        complete: 'Route ready',
      },
      stays: {
        pending: 'Search free ger camps, hotels and events',
        active: 'Searching free ger camps, hotels and events...',
        complete: 'Stays and events found',
      },
      writing: {
        pending: 'Write the itinerary',
        active: 'Writing the itinerary...',
        complete: 'Itinerary ready',
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
      unit: { mn: 'сая₮', en: 'M MNT' },
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
