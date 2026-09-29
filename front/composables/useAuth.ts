import { useApi } from './useApi'
import { API_ENDPOINTS } from '~/constants'
import type { LoginInput, AuthResponse } from '~/types/auth/auth-types'

export const useAuth = () => {
  const api = useApi()
  const router = useRouter()
  const toast = useNuxtApp().$toast
  const cookieAuth = useCookieAuth()

  const loading = ref(false)
  const error = ref<string[]>([])

  const isLoggedIn = computed(() => cookieAuth.isAuthenticated.value)
  const access_token = computed(() => cookieAuth.authToken.value || '')

  const login = async (credentials: LoginInput): Promise<boolean> => {
    loading.value = true
    error.value = []

    try {
      const formData = new URLSearchParams()
      formData.append('grant_type', 'password')
      formData.append('username', credentials.username)
      formData.append('password', credentials.password)

      const { data, error: apiError } = await api.post<AuthResponse>(API_ENDPOINTS.AUTH.LOGIN, formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      })

      if (apiError) {
        error.value = [apiError.message]
        toast.error(apiError.message)
        return false
      }

      if (data) {
        cookieAuth.setAuth(data.access_token, credentials.username)

        toast.success('Login successful')
        await router.push('/')
        return true
      }

      return false
    } catch (err: any) {
      let errorMessage = 'Login failed'

      if (err.status === 401) {
        errorMessage = 'Invalid username or password'
      } else if (err.status >= 500) {
        errorMessage = 'Server error. Please try again later'
      } else if (err.message) {
        errorMessage = err.message
      }

      error.value = [errorMessage]
      toast.error(errorMessage)
      return false
    } finally {
      loading.value = false
    }
  }

  const logout = async () => {
    // Best-effort server-side token revocation; local state is always cleared
    await api.post(API_ENDPOINTS.AUTH.LOGOUT)
    cookieAuth.clearAuth()
    error.value = []
    toast.success('Successfully logged out')
    router.push('/login')
  }

  const checkAuthStatus = (): boolean => {
    return cookieAuth.isAuthenticated.value
  }

  return {
    loading: readonly(loading),
    error: readonly(error),
    isLoggedIn,
    access_token,
    login,
    logout,
    checkAuthStatus,
  }
}
