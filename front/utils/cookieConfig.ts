import { useCookie } from 'nuxt/app'

export interface CookieConfig {
  secure: boolean
  httpOnly: boolean
  sameSite: 'strict' | 'lax' | 'none'
  maxAge: number
}

export const SECURE_COOKIE_CONFIG: CookieConfig = {
  secure: process.env.NODE_ENV === 'production',
  httpOnly: false,
  sameSite: 'strict',
  maxAge: 60 * 60 * 8,
}

export const getAuthCookie = (name: string = 'user-auth') => {
  return useCookie(name, SECURE_COOKIE_CONFIG)
}

export const getEmailCookie = (name: string = 'user-email') => {
  return useCookie(name, SECURE_COOKIE_CONFIG)
}
