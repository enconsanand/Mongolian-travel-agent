<script setup lang="ts">
import { BRAND } from '~/constants/brand'
import BrandMark from '~/components/Common/BrandMark.vue'
import PlannerHeader from '~/components/TripPlanner/PlannerHeader.vue'
import type { ApiError } from '~/utils/errors'

const { mode } = defineProps<{ mode: 'login' | 'register' }>()
const { locale, messages: m } = useAccountMessages()
const route = useRoute()
const api = useApi()
const auth = useAuth()
const draft = useState('auth-contact-draft', () => ({ contact: '', name: '', kind: 'email' as 'email' | 'phone' }))
/** Carries why the visitor was moved between login and register, so the next form can explain it. */
const notice = useState<'' | 'registration_required' | 'account_exists'>('auth-contact-notice', () => '')
const code = ref('')
const challenge = ref<{ challenge_id: string; contact: string } | null>(null)
const busy = ref(false)
const error = ref('')
const cooldown = ref(0)
let timer: ReturnType<typeof setInterval> | undefined
const redirect = computed(() => (typeof route.query.redirect === 'string' ? route.query.redirect : undefined))
const alternate = computed(() => ({
  path: mode === 'login' ? '/register' : '/login',
  query: redirect.value ? { redirect: redirect.value } : {},
}))
const input = ref<HTMLInputElement | null>(null)
function messageFor(key: string) {
  const text = m.value[key as keyof typeof m.value]
  return typeof text === 'string' ? text : m.value.genericError
}
const errorText = computed(() => messageFor(error.value))
/** Shown only on the form the visitor was moved to, not on the one they are leaving. */
const noticeText = computed(() => {
  if (notice.value === 'registration_required' && mode === 'register') return m.value.movedToRegister
  if (notice.value === 'account_exists' && mode === 'login') return m.value.movedToLogin
  return ''
})
/** Which field an error belongs to, so it renders next to that input; anything else stays in the form-level alert. */
const errorField = computed(() => {
  if (['invalidName', 'name_required'].includes(error.value)) return 'name'
  if (['invalidCode', 'code_expired'].includes(error.value)) return 'code'
  if (['invalidContact', 'account_unavailable'].includes(error.value)) return 'contact'
  return error.value ? 'form' : null
})
/** A wrong-door contact goes straight to the other form with the typed contact and redirect kept. */
async function switchForm(reason: 'registration_required' | 'account_exists') {
  notice.value = reason
  await navigateTo(alternate.value)
}
function readError(error: ApiError | null) {
  if (error?.statusCode === 429) return 'rateLimited'
  return (error?.data as { detail?: { code?: string } } | undefined)?.detail?.code || 'genericError'
}
function startCooldown() {
  clearInterval(timer)
  cooldown.value = 30
  timer = setInterval(() => {
    if (cooldown.value > 0) cooldown.value--
    else clearInterval(timer)
  }, 1000)
}
async function send() {
  if (busy.value || (challenge.value && cooldown.value > 0)) return
  error.value = ''
  const contact = draft.value.contact.trim()
  const phone = contact.replace(/[\s()-]/g, '')
  if (draft.value.kind === 'email' ? !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(contact) : !/^(\+976)?[0-9]{8}$/.test(phone)) {
    error.value = 'invalidContact'
    return
  }
  if (mode === 'register' && !draft.value.name.trim()) {
    error.value = 'invalidName'
    return
  }
  busy.value = true
  const result = await api.post<{ challenge_id: string; contact: string }>('/auth/code/request', {
    contact,
    name: draft.value.name.trim(),
    purpose: mode,
    previous_challenge: challenge.value?.challenge_id,
  })
  busy.value = false
  if (!result.data) {
    const reason = readError(result.error)
    if (reason === 'registration_required' || reason === 'account_exists') await switchForm(reason)
    else error.value = reason
    return
  }
  notice.value = ''
  challenge.value = result.data
  code.value = ''
  startCooldown()
  await nextTick()
  input.value?.focus()
}
async function verify() {
  if (busy.value || !challenge.value) return
  error.value = ''
  if (!/^[0-9]{6}$/.test(code.value)) {
    error.value = 'invalidCode'
    return
  }
  busy.value = true
  const result = await api.post<{ access_token: string }>('/auth/code/verify', {
    challenge_id: challenge.value.challenge_id,
    code: code.value,
  })
  if (!result.data) {
    busy.value = false
    const reason = readError(result.error)
    if (reason === 'account_exists') await switchForm(reason)
    else error.value = reason
    return
  }
  const contact = challenge.value.contact
  draft.value = { contact: '', name: '', kind: 'email' }
  await auth.completeLogin(result.data.access_token, contact, redirect.value)
  busy.value = false
}
/** Keep only digits, so a pasted "123 456" or "123-456" still becomes a full code; a complete code submits itself. */
function onCodeInput(event: Event) {
  const target = event.target as HTMLInputElement
  const digits = target.value.replace(/\D/g, '').slice(0, 6)
  target.value = digits
  const completed = digits.length === 6 && code.value.length < 6
  code.value = digits
  if (error.value === 'invalidCode') error.value = ''
  if (completed) verify()
}
function setKind(kind: 'email' | 'phone') {
  notice.value = ''
  draft.value.kind = kind
  draft.value.contact = ''
  error.value = ''
}
function edit() {
  challenge.value = null
  code.value = ''
  error.value = ''
  cooldown.value = 0
  clearInterval(timer)
}
onUnmounted(() => clearInterval(timer))
useHead(() => ({
  title: `${mode === 'login' ? m.value.login : m.value.register} · ${BRAND.name}`,
  htmlAttrs: { lang: locale.value },
}))
</script>

<template>
  <div>
    <PlannerHeader
      :locale="locale"
      :language-group-label="locale === 'mn' ? 'Хэл' : 'Language'"
      @set-locale="locale = $event"
    />
    <main class="mx-auto grid w-full max-w-page items-center gap-10 px-4 py-10 sm:py-16 lg:grid-cols-2 lg:gap-16">
      <div class="hidden lg:block">
        <div class="relative overflow-hidden rounded-card">
          <img src="/images/hero/khuvsgul.jpg" alt="" class="aspect-[4/3] w-full object-cover" />
        </div>
        <h1 class="mt-7 font-display text-3xl leading-snug font-bold">{{ mode === 'login' ? m.welcome : m.join }}</h1>
        <p class="mt-3 leading-relaxed text-ink-muted">{{ m.intro }}</p>
      </div>
      <section class="panel mx-auto w-full max-w-md p-6 sm:p-8">
        <BrandMark class="mb-6 h-11 w-11" />
        <p class="mb-2 text-xs font-semibold tracking-widest text-ink-subtle uppercase">
          {{ challenge ? '02 / 02' : '01 / 02' }}
        </p>
        <h2 class="font-display text-2xl font-bold">
          {{ challenge ? m.codeTitle : mode === 'login' ? m.login : m.register }}
        </h2>
        <p v-if="!challenge" class="mt-3 text-sm leading-relaxed text-ink-muted">
          {{ mode === 'login' ? m.loginHint : m.registerHint }}
        </p>
        <p v-else class="mt-3 text-sm leading-relaxed break-words text-ink-muted" role="status">
          {{ locale === 'en' ? `${m.sent} ${challenge.contact}` : `${challenge.contact} ${m.sent}` }}
        </p>
        <p
          v-if="noticeText && !challenge"
          class="mt-4 flex gap-2 rounded-control bg-brand-soft p-3 text-sm leading-relaxed text-brand"
          role="status"
        >
          <i class="pi pi-info-circle mt-0.5" aria-hidden="true" />
          {{ noticeText }}
        </p>
        <form class="mt-6 space-y-5" @submit.prevent="challenge ? verify() : send()">
          <template v-if="!challenge">
            <label v-if="mode === 'register'" class="block space-y-2 text-sm font-medium">
              <span>{{ m.name }}</span>
              <input
                v-model="draft.name"
                class="planner-date"
                autocomplete="name"
                maxlength="100"
                :placeholder="m.namePlaceholder"
                :disabled="busy"
                :aria-invalid="errorField === 'name'"
                :aria-describedby="errorField === 'name' ? 'auth-error' : undefined"
              />
              <span v-if="errorField === 'name'" id="auth-error" class="block text-sm text-danger" role="alert">
                {{ errorText }}
              </span>
            </label>
            <div class="grid grid-cols-2 gap-2" role="group" :aria-label="m.contact">
              <button
                v-for="kind in ['email', 'phone'] as const"
                :key="kind"
                class="choice-chip"
                type="button"
                :aria-pressed="draft.kind === kind"
                :disabled="busy"
                @click="setKind(kind)"
              >
                {{ m[kind] }}
              </button>
            </div>
            <label class="block space-y-2 text-sm font-medium">
              <span>{{ m[draft.kind] }}</span>
              <input
                v-model="draft.contact"
                class="planner-date"
                :type="draft.kind === 'email' ? 'email' : 'tel'"
                :autocomplete="draft.kind === 'email' ? 'email' : 'tel'"
                :placeholder="draft.kind === 'email' ? 'you@example.com' : '9911 2233'"
                maxlength="254"
                :disabled="busy"
                :aria-invalid="errorField === 'contact'"
                :aria-describedby="errorField === 'contact' ? 'auth-error' : undefined"
              />
              <span v-if="errorField === 'contact'" id="auth-error" class="block text-sm text-danger" role="alert">
                {{ errorText }}
              </span>
            </label>
          </template>
          <label v-else class="block space-y-2 text-sm font-medium">
            <span>{{ m.code }}</span>
            <input
              ref="input"
              :value="code"
              class="planner-date text-center !text-2xl tracking-[0.4em]"
              type="text"
              inputmode="numeric"
              autocomplete="one-time-code"
              pattern="[0-9]*"
              placeholder="000000"
              :disabled="busy"
              :aria-invalid="errorField === 'code'"
              :aria-describedby="errorField === 'code' ? 'auth-error' : undefined"
              @input="onCodeInput"
            />
            <span v-if="errorField === 'code'" id="auth-error" class="block text-sm text-danger" role="alert">
              {{ errorText }}
            </span>
          </label>
          <p v-if="errorField === 'form'" class="rounded-control bg-danger-soft p-3 text-sm text-danger" role="alert">
            {{ errorText }}
          </p>
          <button type="submit" class="btn-primary min-h-12 w-full px-4 py-3 disabled:opacity-60" :disabled="busy">
            <i
              :class="busy ? 'pi pi-spinner pi-spin' : challenge ? 'pi pi-check' : 'pi pi-arrow-right'"
              aria-hidden="true"
            />
            {{ busy ? m.working : challenge ? m.verify : m.send }}
          </button>
          <div v-if="challenge" class="flex flex-wrap justify-between gap-3 text-sm">
            <button
              type="button"
              class="text-brand disabled:text-ink-subtle"
              :disabled="busy || cooldown > 0"
              @click="send"
            >
              {{ m.resend }}{{ cooldown ? ` (${cooldown}${m.seconds})` : '' }}
            </button>
            <button type="button" class="text-ink-muted" :disabled="busy" @click="edit">{{ m.editContact }}</button>
          </div>
        </form>
        <p class="mt-5 rounded-control bg-accent-soft p-3 text-xs leading-relaxed text-accent-ink">{{ m.demo }}</p>
        <p class="mt-6 text-center text-sm text-ink-muted">
          {{ mode === 'login' ? m.noAccount : m.hasAccount }}
          <NuxtLink :to="alternate" class="ml-1 font-semibold text-brand" @click="notice = ''">
            {{ mode === 'login' ? m.register : m.login }}
          </NuxtLink>
        </p>
      </section>
    </main>
  </div>
</template>
