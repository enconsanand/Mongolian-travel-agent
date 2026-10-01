<script setup lang="ts">
import BrandMark from '~/components/Common/BrandMark.vue'
import { BRAND } from '~/constants/brand'

definePageMeta({
  layout: 'guest',
})

const auth = useAuth()
const route = useRoute()
const { form: loginForm, errors, isValid, validateForm } = useLoginForm()

const handleLogin = async (): Promise<void> => {
  if (!validateForm()) return

  const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : null
  await auth.login(
    {
      username: loginForm.value.username,
      password: loginForm.value.password,
    },
    redirect
  )
}
</script>

<template>
  <div class="mx-auto w-full max-w-md p-6">
    <p class="mb-6 text-center">
      <BrandMark class="mx-auto mb-3 h-12 w-12" />
      <span class="font-display text-2xl font-bold text-ink">{{ BRAND.name }}</span>
    </p>

    <div class="panel overflow-hidden">
      <div class="border-b border-line px-8 py-5">
        <h1 class="text-center text-lg font-semibold">Sign in</h1>
      </div>

      <form class="space-y-6 px-8 py-8" @submit.prevent="handleLogin">
        <div class="space-y-2">
          <label for="username" class="block text-sm font-medium text-ink">Username</label>
          <InputText
            id="username"
            v-model="loginForm.username"
            type="text"
            placeholder="Enter your username"
            class="h-12 w-full"
            :invalid="!!errors.username"
            autocomplete="username"
            required
          />
          <small v-if="errors.username" class="block text-sm text-danger">
            {{ errors.username }}
          </small>
        </div>

        <div class="space-y-2">
          <label for="password" class="block text-sm font-medium text-ink">Password</label>
          <Password
            id="password"
            v-model="loginForm.password"
            placeholder="Enter your password"
            class="w-full"
            input-class="h-12 w-full"
            :invalid="!!errors.password"
            autocomplete="current-password"
            required
            toggle-mask
            fluid
            :feedback="false"
          />
          <small v-if="errors.password" class="block text-sm text-danger">
            {{ errors.password }}
          </small>
        </div>

        <button
          type="submit"
          class="btn-primary h-12 w-full disabled:opacity-60"
          :disabled="!isValid || auth.loading.value"
        >
          <i :class="auth.loading.value ? 'pi pi-spinner pi-spin' : 'pi pi-sign-in'" aria-hidden="true" />
          {{ auth.loading.value ? 'Signing in...' : 'Sign in' }}
        </button>

        <div
          v-if="auth.error.value.length > 0"
          class="rounded-control bg-danger-soft p-3 text-sm text-danger"
          role="alert"
        >
          <p v-for="error in auth.error.value" :key="error">{{ error }}</p>
        </div>
      </form>
    </div>
  </div>
</template>
