import { usePreferredDark } from '@vueuse/core'

export type Theme = 'light' | 'dark'

/**
 * Light or dark: follows the system until the visitor picks one, then remembers it in a cookie so the
 * server renders the same theme (no flash, and no inline script that the CSP would block).
 */
export function useTheme() {
  const chosen = useCookie<Theme | null>('theme', { default: () => null, sameSite: 'lax', maxAge: 60 * 60 * 24 * 365 })
  const systemDark = usePreferredDark()
  const theme = computed<Theme>(() => chosen.value ?? (systemDark.value ? 'dark' : 'light'))

  function toggle() {
    chosen.value = theme.value === 'dark' ? 'light' : 'dark'
  }

  return { chosen, theme, toggle }
}
