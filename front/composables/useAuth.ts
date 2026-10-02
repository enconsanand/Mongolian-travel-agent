import { useApi } from './useApi'
import { API_ENDPOINTS } from '~/constants'

export const useAuth = () => {
  const api = useApi()
  const router = useRouter()
  const cookieAuth = useCookieAuth()

  const isLoggedIn = computed(() => cookieAuth.isAuthenticated.value)

  /** Only a path on this site: never an absolute or protocol-relative URL (open redirect) */
  const safeRedirect = (redirect?: string | null): string =>
    redirect && redirect.startsWith('/') && !redirect.startsWith('//') && !redirect.startsWith('/\\') ? redirect : '/'

  const completeLogin = async (token: string, contact: string, redirect?: string | null) => {
    cookieAuth.setAuth(token, contact)
    await router.push(safeRedirect(redirect))
  }

  const logout = async () => {
    // Best-effort server-side token revocation; local state is always cleared
    await api.post(API_ENDPOINTS.AUTH.LOGOUT)
    cookieAuth.clearAuth()
    router.push('/login')
  }

  return {
    isLoggedIn,
    logout,
    completeLogin,
    safeRedirect,
  }
}
