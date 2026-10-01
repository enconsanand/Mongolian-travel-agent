import type { AppLocale } from '~/types/trip-planner'

export type HeroLayout = 'orbit' | 'sun' | 'arch'

export interface HeroSlide {
  id: string
  image: string
  /** Where the photo is anchored when it is cropped into its frame */
  focus: string
  /** Each slide has its own composition of frame and colour shapes */
  layout: HeroLayout
  title: Record<AppLocale, string>
}

export const HERO_SLIDES: readonly HeroSlide[] = [
  {
    id: 'statue',
    image: '/images/hero/statue.jpg',
    focus: '50% 30%',
    layout: 'orbit',
    title: { mn: 'Чингис хааны морьт хөшөө', en: 'Chinggis Khaan Equestrian Statue' },
  },
  {
    id: 'toono',
    image: '/images/hero/toono.jpg',
    focus: '50% 40%',
    layout: 'sun',
    title: { mn: 'Гэрийн тооно', en: 'The ger’s crown, the toono' },
  },
  {
    id: 'painted-toono',
    image: '/images/hero/painted-toono.jpg',
    focus: '50% 35%',
    layout: 'arch',
    title: { mn: 'Хээ угалзтай тооно', en: 'A painted toono' },
  },
]
