import { z } from 'zod'

const MALICIOUS_PATTERNS = [/<script/i, /javascript:/i, /onclick=/i, /onerror=/i, /onload=/i]
const EMAIL_REGEX = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/
const PHONE_REGEX = /^\d{8}$/

export const sanitizeInput = (value: string): string => {
  if (typeof value !== 'string') return ''
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#x27;')
    .replace(/\//g, '&#x2F;')
}

const checkMaliciousPatterns = (input: string): boolean => {
  return MALICIOUS_PATTERNS.some((pattern) => pattern.test(input))
}

export const commonValidations = {
  required: z.string().min(1, 'This field is required'),

  email: z
    .string()
    .min(1, 'Email is required')
    .min(3, 'Email too short')
    .max(254, 'Email too long')
    .regex(EMAIL_REGEX, 'Valid email required')
    .refine((email) => !checkMaliciousPatterns(email), 'Invalid characters in email'),

  emailOptional: z
    .string()
    .optional()
    .refine((email) => {
      if (!email || email === '') return true
      return EMAIL_REGEX.test(email)
    }, 'Invalid email format'),

  password: z
    .string()
    .min(1, 'Password is required')
    .min(6, 'Password must be at least 6 characters')
    .max(128, 'Password too long'),

  passwordLegacy: z.string().regex(/^[A-Za-z\d]{6,16}$/, 'Password must be 6-16 characters'),

  phoneNumber: z.string().regex(PHONE_REGEX, 'Invalid phone number'),

  positiveNumber: z
    .number()
    .min(0, 'Cannot be negative')
    .or(
      z
        .string()
        .transform((val) => Number(val))
        .pipe(z.number().min(0, 'Cannot be negative'))
    ),
}

export const required = (v: any) => (v !== undefined && v !== '') || 'This field is required'

export const validateEmailSecure = (email: string): boolean | string => {
  const result = commonValidations.email.safeParse(email)
  return result.success ? true : result.error.issues[0]?.message || 'Invalid email'
}

export const validatePasswordSecure = (password: string): boolean | string => {
  const result = commonValidations.password.safeParse(password)
  return result.success ? true : result.error.issues[0]?.message || 'Invalid password'
}

export const validateEmail = (v: any) => {
  const result = commonValidations.emailOptional.safeParse(v)
  return result.success ? true : result.error.issues[0]?.message || 'Invalid email format'
}

export const validatePasswordLegacy = (inputString: string) => {
  const result = commonValidations.passwordLegacy.safeParse(inputString)
  return result.success ? true : result.error.issues[0]?.message || 'Password must be 6-16 characters'
}

export const validatePhoneNumber = (v: any) => {
  const result = commonValidations.phoneNumber.safeParse(v)
  return result.success ? true : result.error.issues[0]?.message || 'Invalid phone number'
}

export const notMinusNumber = (v: any) => {
  const result = commonValidations.positiveNumber.safeParse(v)
  return result.success ? true : result.error.issues[0]?.message || 'Cannot be negative'
}
