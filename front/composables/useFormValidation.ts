import type { ZodType } from 'zod'
import { ZodError } from 'zod'

export interface ValidationResult {
  isValid: boolean
  errors: Record<string, string>
  firstError?: string
}

export interface UseFormValidationReturn<T> {
  validate: (data: T) => ValidationResult
  validateField: (field: keyof T, value: any) => string | undefined
  clearError: (field: keyof T) => void
  clearAllErrors: () => void
  errors: Ref<Record<string, string>>
  isValid: ComputedRef<boolean>
  hasErrors: ComputedRef<boolean>
}

export function useFormValidation<T extends Record<string, any>>(
  schema: ZodType<T>,
  formData?: Ref<T>
): UseFormValidationReturn<T> {
  const errors = ref<Record<string, string>>({})

  const validate = (data: T): ValidationResult => {
    try {
      schema.parse(data)
      errors.value = {}
      return {
        isValid: true,
        errors: {},
      }
    } catch (error) {
      if (error instanceof ZodError) {
        const fieldErrors: Record<string, string> = {}

        error.issues.forEach((err) => {
          const path = err.path.join('.')
          if (path) {
            fieldErrors[path] = err.message
          }
        })

        errors.value = fieldErrors
        return {
          isValid: false,
          errors: fieldErrors,
          firstError: Object.values(fieldErrors)[0],
        }
      }

      return {
        isValid: false,
        errors: { general: 'Validation failed' },
        firstError: 'Validation failed',
      }
    }
  }

  const validateField = (field: keyof T, value: any): string | undefined => {
    try {
      const schemaAny = schema as any
      if (schemaAny.shape && field in schemaAny.shape) {
        const fieldSchema = schemaAny.shape[field as string]
        if (fieldSchema && typeof fieldSchema.parse === 'function') {
          fieldSchema.parse(value)

          if (errors.value[field as string]) {
            const { [field as string]: _, ...rest } = errors.value
            errors.value = rest
          }
          return undefined
        }
      }

      return undefined
    } catch (error) {
      if (error instanceof ZodError) {
        const errorMessage = error.issues[0]?.message || 'Invalid value'
        errors.value[field as string] = errorMessage
        return errorMessage
      }

      const errorMessage = 'Invalid value'
      errors.value[field as string] = errorMessage
      return errorMessage
    }
  }

  const clearError = (field: keyof T): void => {
    if (errors.value[field as string]) {
      const { [field as string]: _, ...rest } = errors.value
      errors.value = rest
    }
  }

  const clearAllErrors = (): void => {
    errors.value = {}
  }

  const isValid = computed(() => {
    if (!formData?.value) return false
    return validate(formData.value).isValid
  })

  const hasErrors = computed(() => {
    return Object.keys(errors.value).length > 0
  })

  return {
    validate,
    validateField,
    clearError,
    clearAllErrors,
    errors,
    isValid,
    hasErrors,
  }
}
