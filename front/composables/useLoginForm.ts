import { loginFormSchema, type LoginFormInput } from '~/lib/validations/auth'

export interface UseLoginFormReturn {
  form: Ref<LoginFormInput>
  errors: ComputedRef<Record<string, string>>
  isValid: ComputedRef<boolean>
  hasErrors: ComputedRef<boolean>
  validateForm: () => boolean
  validateField: (field: keyof LoginFormInput, value: any) => string | undefined
  clearError: (field: keyof LoginFormInput) => void
  clearAllErrors: () => void
  resetForm: () => void
}

export function useLoginForm(initialData?: Partial<LoginFormInput>): UseLoginFormReturn {
  const form = ref<LoginFormInput>({
    username: '',
    password: '',
    remember: false,
    ...initialData,
  })

  const validation = useFormValidation(loginFormSchema)
  const hasInteracted = ref(false)
  const showErrors = ref(false)

  const validateForm = (): boolean => {
    showErrors.value = true
    const result = validation.validate(form.value)
    return result.isValid
  }

  const resetForm = (): void => {
    form.value = {
      username: '',
      password: '',
      remember: false,
      ...initialData,
    }
    validation.clearAllErrors()
    showErrors.value = false
    hasInteracted.value = false
  }

  const errors = computed(() => {
    if (!showErrors.value && !hasInteracted.value) {
      return {}
    }
    return validation.errors.value
  })

  watch(
    () => form.value.username,
    (newValue, oldValue) => {
      if (newValue !== oldValue && newValue.length > 0) {
        hasInteracted.value = true
      }
    }
  )

  watch(
    () => form.value.password,
    (newValue, oldValue) => {
      if (newValue !== oldValue && newValue.length > 0) {
        hasInteracted.value = true
      }
    }
  )

  onMounted(() => {
    setTimeout(() => {
      if (form.value.username.length > 0 || form.value.password.length > 0) {
        hasInteracted.value = true
      }
    }, 500)
  })

  const isValid = computed(() => {
    return form.value.username.trim().length > 0 && form.value.password.length >= 6
  })

  return {
    form,
    errors,
    isValid,
    hasErrors: validation.hasErrors,
    validateForm,
    validateField: validation.validateField,
    clearError: validation.clearError,
    clearAllErrors: validation.clearAllErrors,
    resetForm,
  }
}
