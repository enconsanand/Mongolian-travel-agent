import { z } from 'zod'
import { commonValidations } from '~/utils/validates'

export const loginSchema = z.object({
  username: z.string().min(1, 'Username is required').max(50, 'Username must be less than 50 characters').trim(),
  password: commonValidations.password,
})

export const loginFormSchema = loginSchema.extend({
  remember: z.boolean().optional().default(false),
})

export type LoginInput = z.infer<typeof loginSchema>
export type LoginFormInput = z.infer<typeof loginFormSchema>

export const validateUsername = (username: string): string | undefined => {
  const result = commonValidations.required.max(50, 'Username must be less than 50 characters').safeParse(username)
  return result.success ? undefined : result.error.issues[0]?.message
}

export const validatePassword = (password: string): string | undefined => {
  const result = commonValidations.password.safeParse(password)
  return result.success ? undefined : result.error.issues[0]?.message
}
