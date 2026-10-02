import type { AppLocale } from '~/types/trip-planner'

/** The language the traveller picked, shared by every page; Mongolian until they switch. */
export const useAppLocale = () => useState<AppLocale>('app-locale', () => 'mn')
