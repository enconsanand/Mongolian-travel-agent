import { getAuthCookie, getEmailCookie } from '~/utils/cookieConfig'
import { COOKIE_NAMES } from '~/constants'

// UX-level check only: rejects expired/malformed tokens at the route guard.
// The backend still verifies the JWT signature on every API call.
const hasValidExpiry = (token: string | null | undefined): boolean => {
  if (!token) return false
  try {
    const part = token.split('.')[1]
    if (!part) return false
    const base64 = part.replace(/-/g, '+').replace(/_/g, '/')
    const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), '=')
    const payload = JSON.parse(atob(padded))
    return typeof payload.exp === 'number' && payload.exp * 1000 > Date.now()
  } catch {
    return false
  }
}

export const useCookieAuth = () => {
  const authCookie = getAuthCookie(COOKIE_NAMES.AUTH_TOKEN)
  const emailCookie = getEmailCookie(COOKIE_NAMES.USER_EMAIL)

  const isAuthenticated = computed(() => hasValidExpiry(authCookie.value))
  const userEmail = computed(() => emailCookie.value || '')

  const setAuth = (token: string, email: string) => {
    authCookie.value = token
    emailCookie.value = email
  }

  const clearAuth = () => {
    authCookie.value = null
    emailCookie.value = null
  }

  return {
    isAuthenticated,
    userEmail,
    setAuth,
    clearAuth,
    authToken: computed(() => authCookie.value),
  }
}
