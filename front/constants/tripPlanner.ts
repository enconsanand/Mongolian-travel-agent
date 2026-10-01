import { BRAND } from '~/constants/brand'
import type { AppLocale, TripPlannerMessages } from '~/types/trip-planner'

/** When each planning step is shown as started while the request runs (the server does them in this order) */
export const PLAN_STEP_STARTS_MS = { places: 2500, stays: 5000, writing: 8000 } as const

export const VOICE_METER_DELAYS_MS = [0, 150, 300, 450, 200] as const

export const TRIP_PLANNER_MESSAGES: Record<AppLocale, TripPlannerMessages> = {
  mn: {
    documentTitle: `${BRAND.name}: аяллын хөтөлбөр`,
    languageGroupLabel: 'Хэл',
    heroTitle: 'Монголоор аялах хөтөлбөрөө төлөвлөе',
    heroSubtitle:
      'Юу үзэж, юу хиймээр байгаагаа бичих эсвэл хэлээрэй. Бид өдөр бүрийн маршрут, захиалах боломжтой буудлыг санал болгоно.',
    requestLabel: 'Хаашаа аялмаар байна?',
    requestPlaceholder: 'Хаашаа, хэдүүлээ, хэдэн хоног аялах вэ?',
    tapToSpeak: 'Дуугаар оруулах',
    listening: 'Сонсож байна… зогсоохын тулд дахин дарна уу',
    voiceButtonLabel: 'Монгол хэлээр дуут оруулалт',
    generate: 'Илгээх',
    retry: 'Дахин оролдох',
    chat: {
      ask: {
        guests: 'Сайхан санаа байна. Хэдүүлээ явах вэ?',
        dates: 'Хэзээ, хэдэн хоног явах вэ? Жишээ нь "10 сарын 5-наас 4 хоног".',
        budget: 'Нийт төсөв хэр орчим бэ? Хязгааргүй бол "хязгааргүй" гэж бичээрэй.',
      },
      planning: 'Ойлголоо. Хөтөлбөр бэлдэж байна, ихэвчлэн 10–30 секунд болно.',
      revising: 'За, хөтөлбөрийг шинэчилж байна.',
      planned: 'Танд зориулсан хөтөлбөр бэлэн. Өөрчлөх зүйл байвал доор бичээрэй.',
      revised: 'Шинэчиллээ. Өөр юм өөрчлөх үү?',
      agentName: `${BRAND.name} агент`,
      replyPlaceholder: 'Хариулт эсвэл өөрчлөлтөө бичих',
      newTrip: 'Шинэ аялал',
      openPlan: 'Дэлгэрэнгүй, захиалах',
      days: 'өдөр',
      total: 'Нийт',
    },
    errors: {
      planner_unavailable: 'Төлөвлөгч түр ажиллахгүй байна. Хэсэг хүлээгээд дахин оролдоно уу.',
      error: 'Хөтөлбөр үүсгэж чадсангүй. Дахин оролдоно уу.',
    },
    steps: {
      intent: {
        pending: 'Хүсэлтийг ойлгох',
        active: 'Хүсэлтийг ойлгож байна...',
        complete: 'Хүсэлтийг ойлголоо',
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
    documentTitle: `${BRAND.name}: plan your trip`,
    languageGroupLabel: 'Language',
    heroTitle: 'Plan your journey through Mongolia',
    heroSubtitle:
      'Tell us what you would like to see and do. We will suggest a day-by-day route with stays you can book.',
    requestLabel: 'Where would you like to go?',
    requestPlaceholder: 'Where to, how many of you, and for how long?',
    tapToSpeak: 'Speak your request',
    listening: 'Listening… tap again to stop',
    voiceButtonLabel: 'Speak your request',
    generate: 'Send',
    retry: 'Try again',
    chat: {
      ask: {
        guests: 'Sounds lovely. How many of you are going?',
        dates: 'When, and for how many days? For example "4 days from Oct 5".',
        budget: 'Roughly what is your total budget? Say "no limit" if there is none.',
      },
      planning: 'Got it. Putting your itinerary together, this usually takes 10–30 seconds.',
      revising: 'Sure, updating the itinerary.',
      planned: 'Here is an itinerary for you. Tell me below if you want anything changed.',
      revised: 'Updated. Anything else to change?',
      agentName: `${BRAND.name} agent`,
      replyPlaceholder: 'Reply or ask for a change',
      newTrip: 'New trip',
      openPlan: 'Details and booking',
      days: 'days',
      total: 'Total',
    },
    errors: {
      planner_unavailable: 'The planner is unavailable right now. Please try again in a moment.',
      error: 'Could not create the itinerary. Please try again.',
    },
    steps: {
      intent: {
        pending: 'Understand your request',
        active: 'Understanding your request...',
        complete: 'Request understood',
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
