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
  author: string
  license: string
  source: string
}

/** Wikimedia Commons photos of places visitors ask for first, then the eastern and Gobi guide. */
export const HERO_SLIDES: readonly HeroSlide[] = [
  {
    id: 'khuvsgul',
    image: '/images/hero/khuvsgul.jpg',
    focus: '50% 40%',
    layout: 'sun',
    title: { mn: 'Хөвсгөл нуур', en: 'Lake Khövsgöl' },
    author: 'Bernard Gagnon',
    license: 'CC0',
    source: 'https://commons.wikimedia.org/wiki/File:Lake_Kh%C3%B6vsg%C3%B6l,_Mongolia.jpg',
  },
  {
    id: 'uvs',
    image: '/images/hero/uvs.jpg',
    focus: '50% 45%',
    layout: 'arch',
    title: { mn: 'Увс нуур', en: 'Uvs Lake' },
    author: 'Jan Sysel',
    license: 'CC BY-SA 3.0',
    source: 'https://commons.wikimedia.org/wiki/File:Uvs_n%C3%BAr.JPG',
  },
  {
    id: 'gobi',
    image: '/images/hero/gobi.jpg',
    focus: '50% 65%',
    layout: 'orbit',
    title: { mn: 'Говийн цөл', en: 'Gobi Desert' },
    author: 'Richard Mortel',
    license: 'CC BY 2.0',
    source: 'https://commons.wikimedia.org/wiki/File:Gobi_Desert_dunes.jpg',
  },
  {
    id: 'khukh-nuur',
    image: '/images/hero/khukh-nuur.jpg',
    focus: '50% 55%',
    layout: 'sun',
    title: { mn: 'Хар зүрхний хөх нуур', en: 'Khar Zürkh Blue Lake' },
    author: 'Ujin bold',
    license: 'CC BY 4.0',
    source:
      'https://commons.wikimedia.org/wiki/File:Khukh_Nuur_(Blue_Lake)_Surrounded_by_Forests_in_Khentii_Province,_Mongolia.jpg',
  },
  {
    id: 'dadal-statue',
    image: '/images/hero/dadal-statue.jpg',
    focus: '50% 35%',
    layout: 'orbit',
    title: { mn: 'Чингис хааны хөшөө, Дадал', en: 'Chinggis monument, Dadal' },
    author: 'Chinneeb',
    license: 'CC BY-SA 3.0',
    source: 'https://commons.wikimedia.org/wiki/File:Chingghis_statue_at_Dadal_sum.JPG',
  },
  {
    id: 'buir',
    image: '/images/hero/buir.jpg',
    focus: '50% 80%',
    layout: 'arch',
    title: { mn: 'Буйр нуур', en: 'Buir Lake' },
    author: 'baterdene_0933',
    license: 'CC BY 3.0',
    source:
      'https://commons.wikimedia.org/wiki/File:%D0%91%D1%83%D0%B9%D1%80_%D0%BD%D1%83%D1%83%D1%80_-%D0%94%D0%BE%D1%80%D0%BD%D0%BE%D0%B4_%D0%B0%D0%B9%D0%BC%D0%B0%D0%B3_%D0%A5%D0%B0%D0%BB%D1%85%D0%B3%D0%BE%D0%BB_%D1%81%D1%83%D0%BC_-_panoramio.jpg',
  },
  {
    id: 'shiliin-bogd',
    image: '/images/hero/shiliin-bogd.jpg',
    focus: '50% 40%',
    layout: 'sun',
    title: { mn: 'Шилийн богд', en: 'Shiliin Bogd' },
    author: 'Gologmine',
    license: 'CC BY-SA 4.0',
    source: 'https://commons.wikimedia.org/wiki/File:Shiliin_bogd.jpg',
  },
  {
    id: 'khamar',
    image: '/images/hero/khamar.jpg',
    focus: '50% 40%',
    layout: 'orbit',
    title: { mn: 'Хамарын хийд', en: 'Khamar Monastery' },
    author: 'Tsend',
    license: 'CC BY 3.0',
    source: 'https://commons.wikimedia.org/wiki/File:Khamar_Monastery.jpg',
  },
  {
    id: 'khongor',
    image: '/images/hero/khongor.jpg',
    focus: '50% 55%',
    layout: 'arch',
    title: { mn: 'Хонгорын элс', en: 'Khongoryn Els' },
    author: 'Bernard Gagnon',
    license: 'CC0',
    source: 'https://commons.wikimedia.org/wiki/File:Khongoryn_Els_04.jpg',
  },
  {
    id: 'khermen',
    image: '/images/hero/khermen.jpg',
    focus: '50% 55%',
    layout: 'sun',
    title: { mn: 'Хэрмэн цав', en: 'Khermen Tsav' },
    author: 'Mongolia Expeditions',
    license: 'CC BY 3.0',
    source: 'https://commons.wikimedia.org/wiki/File:Khermen_Tsav_-_Shambala_gate_-_panoramio.jpg',
  },
  {
    id: 'yolyn-am',
    image: '/images/hero/yolyn-am.jpg',
    focus: '50% 45%',
    layout: 'orbit',
    title: { mn: 'Ёлын ам', en: 'Yolyn Am' },
    author: 'Römert',
    license: 'CC BY-SA 4.0',
    source: 'https://commons.wikimedia.org/wiki/File:Yolyn_Am_2015_(1).JPG',
  },
]
