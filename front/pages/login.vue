<script setup lang="ts">
definePageMeta({
  layout: 'guest',
})

const auth = useAuth()
const { form: loginForm, errors, isValid, validateForm } = useLoginForm()

const handleLogin = async (): Promise<void> => {
  if (!validateForm()) return

  await auth.login({
    username: loginForm.value.username,
    password: loginForm.value.password,
  })
}
</script>

<template>
  <div class="relative w-full max-w-md mx-auto p-6">
    <div class="absolute inset-0 -z-10 overflow-hidden">
      <div
        class="absolute bottom-0 right-0 w-24 h-24 bg-linear-to-br from-blue-500/10 to-purple-500/5 rounded-full blur-xl"
      />
    </div>

    <div class="relative group">
      <div
        class="absolute -inset-1 bg-linear-to-r from-blue-600/20 via-purple-600/10 to-blue-600/20 rounded-2xl blur-lg opacity-0 group-hover:opacity-100 transition-opacity duration-500"
      />

      <div
        class="relative bg-white/95 backdrop-blur-xl rounded-2xl shadow-2xl border border-slate-200/50 overflow-hidden"
      >
        <div class="relative px-8 py-6 bg-linear-to-r from-slate-50/80 to-blue-50/60 border-b border-slate-200/50">
          <div class="absolute inset-0 opacity-5">
            <svg viewBox="0 0 100 20" xmlns="http://www.w3.org/2000/svg" class="w-full h-full">
              <pattern id="header-pattern" x="0" y="0" width="20" height="20" patternUnits="userSpaceOnUse">
                <rect
                  width="20"
                  height="20"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="0.5"
                  class="text-blue-600"
                />
              </pattern>
              <rect width="100" height="20" fill="url(#header-pattern)" />
            </svg>
          </div>

          <div class="relative text-center">
            <h3 class="text-lg font-medium text-slate-900 tracking-wide mb-1">Sign In</h3>
          </div>
        </div>

        <form class="px-8 py-8 space-y-7" @submit.prevent="handleLogin">
          <div class="space-y-3">
            <label for="username" class="block text-sm font-medium text-slate-700 tracking-wide">
              <i class="pi pi-user mr-2 text-slate-500" />
              Username
            </label>
            <InputText
              id="username"
              v-model="loginForm.username"
              type="text"
              placeholder="Enter your username"
              class="w-full h-14 px-5 rounded-xl border-2 border-slate-200 bg-white/90 text-slate-900 focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500 transition-all duration-300 font-light placeholder:text-slate-400 hover:border-slate-300"
              :invalid="!!errors.username"
              autocomplete="username"
              required
            />
            <small v-if="errors.username" class="text-red-500 block text-sm ml-1">
              {{ errors.username }}
            </small>
          </div>

          <div class="space-y-3">
            <label for="password" class="block text-sm font-medium text-slate-700 tracking-wide">
              <i class="pi pi-lock mr-2 text-slate-500" />
              Password
            </label>
            <Password
              id="password"
              v-model="loginForm.password"
              placeholder="Enter your password"
              class="w-full"
              input-class="w-full h-14 px-5 pr-14 rounded-xl border-2 border-slate-200 bg-white/90 text-slate-900 focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500 transition-all duration-300 font-light placeholder:text-slate-400 hover:border-slate-300"
              :invalid="!!errors.password"
              autocomplete="current-password"
              required
              toggle-mask
              fluid
              :feedback="false"
            />
            <small v-if="errors.password" class="text-red-500 block text-sm ml-1">
              {{ errors.password }}
            </small>
          </div>

          <div class="pt-2">
            <Button
              type="submit"
              class="relative w-full h-16 bg-linear-to-r from-blue-600 via-blue-700 to-blue-800 hover:from-blue-700 hover:via-blue-800 hover:to-blue-900 text-white font-medium rounded-xl shadow-xl hover:shadow-2xl transition-all duration-300 transform hover:scale-[1.02] active:scale-[0.98] overflow-hidden group"
              :loading="auth.loading.value"
              :disabled="!isValid || auth.loading.value"
              size="large"
            >
              <div
                class="absolute inset-0 bg-linear-to-r from-transparent via-white/10 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-1000"
              />

              <div class="relative flex items-center justify-center space-x-3">
                <i class="pi pi-sign-in" />
                <span v-if="!auth.loading.value" class="tracking-wide font-medium">Sign In</span>
                <span v-else class="tracking-wide font-medium">Signing in...</span>
              </div>
            </Button>
          </div>

          <Message
            v-if="auth.error.value.length > 0"
            severity="error"
            :closable="false"
            class="mt-6 border-red-200! bg-red-50! rounded-xl!"
          >
            <template #default>
              <div class="flex flex-col space-y-1">
                <span v-for="error in auth.error.value" :key="error" class="text-sm text-red-700">
                  {{ error }}
                </span>
              </div>
            </template>
          </Message>
        </form>
      </div>
    </div>
  </div>
</template>
