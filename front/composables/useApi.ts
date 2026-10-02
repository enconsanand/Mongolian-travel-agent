import { navigateTo } from 'nuxt/app'
import type { FetchError, FetchOptions } from 'ofetch'
import { getAuthCookie } from '~/utils/cookieConfig'
import { COOKIE_NAMES, HTTP_STATUS, ROUTES } from '~/constants'
import { ApiError, AuthError, NetworkError } from '~/utils/errors'

interface ApiResponse<T> {
  data: T | null
  error: ApiError | null
}

type RequestOptions = FetchOptions<'json'> | FetchOptions<'blob'>

export const useApi = () => {
  const config = useRuntimeConfig()
  const router = useRouter()
  const baseURL = config.public.apiBase

  const apiFetch = async <T>(path: string, options: RequestOptions): Promise<ApiResponse<T>> => {
    const headers = new Headers(options.headers)
    const token = getAuthCookie(COOKIE_NAMES.AUTH_TOKEN).value
    if (token && !headers.has('Authorization')) {
      headers.set('Authorization', `Bearer ${token}`)
    }

    try {
      const data = (await $fetch(`${baseURL}${path}`, { ...options, headers } as Parameters<typeof $fetch>[1])) as T
      return { data, error: null }
    } catch (error) {
      return { data: null, error: toApiError(error as FetchError) }
    }
  }

  const toApiError = (error: FetchError): ApiError => {
    const statusCode = error.statusCode

    if (statusCode === HTTP_STATUS.UNAUTHORIZED) {
      getAuthCookie(COOKIE_NAMES.AUTH_TOKEN).value = null
      navigateTo({ path: ROUTES.LOGIN, query: { redirect: router.currentRoute.value.fullPath } })
      return new AuthError('Session expired. Please login again.')
    }

    if (statusCode === HTTP_STATUS.FORBIDDEN) {
      navigateTo(ROUTES.FORBIDDEN)
      return new ApiError('Access denied', HTTP_STATUS.FORBIDDEN)
    }

    if (import.meta.client && !navigator.onLine) {
      return new NetworkError('No internet connection')
    }

    const detail = error.data?.detail
    return new ApiError(typeof detail === 'string' ? detail : error.message, statusCode, error.data)
  }

  return {
    get: <T>(path: string, options?: RequestOptions) => apiFetch<T>(path, { ...options, method: 'GET' }),

    post: <T>(path: string, body?: FetchOptions['body'], options?: RequestOptions) =>
      apiFetch<T>(path, { ...options, method: 'POST', body }),
  }
}
