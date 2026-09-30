<script setup lang="ts">
import MongoliaMapBackdrop from '~/components/TripPlanner/MongoliaMapBackdrop.vue'
import PlanDayCard from '~/components/TripPlan/PlanDayCard.vue'
import PlanOverview from '~/components/TripPlan/PlanOverview.vue'
import PlannerHeader from '~/components/TripPlanner/PlannerHeader.vue'
import { PLAN_MESSAGES } from '~/constants/tripPlan'

definePageMeta({ layout: 'planner', auth: false })

const route = useRoute()
const { locale, proposal, loading, busy, error, staysChanged, canBook, load, revise, accept } = useTripPlan(
  String(route.params.id)
)
const auth = useCookieAuth()
const messages = computed(() => PLAN_MESSAGES[locale.value])
const change = ref('')

const errorMessage = computed(() => {
  if (!error.value || error.value === 'proposal_not_found') return null
  if (error.value === 'planner_unavailable') return messages.value.plannerDown
  if (error.value === 'no_stays') return messages.value.nothingToBook
  return messages.value.genericError
})

async function submitChange() {
  if (await revise(change.value)) change.value = ''
}

onMounted(load)
useHead(() => ({ title: messages.value.title, htmlAttrs: { lang: locale.value } }))
</script>

<template>
  <div>
    <MongoliaMapBackdrop />
    <PlannerHeader
      :locale="locale"
      :language-group-label="locale === 'mn' ? 'Хэл' : 'Language'"
      @set-locale="locale = $event"
    />

    <main class="mx-auto max-w-3xl px-4 pt-8 pb-40">
      <p v-if="loading && !proposal" class="text-slate-400">{{ messages.loading }}</p>

      <section v-else-if="!proposal" class="glass-panel rounded-2xl p-6 text-center">
        <p class="text-slate-300">{{ messages.notFound }}</p>
        <NuxtLink to="/" class="generate-button mt-4 inline-block rounded-lg px-5 py-2.5 font-semibold text-slate-900">
          {{ messages.backToPlanner }}
        </NuxtLink>
      </section>

      <template v-else>
        <div class="flex items-baseline justify-between gap-3">
          <h1 class="text-2xl font-bold tracking-tight sm:text-3xl">{{ messages.title }}</h1>
          <span class="shrink-0 text-xs text-slate-400">{{ messages.version }} {{ proposal.version }}</span>
        </div>

        <div class="mt-5">
          <PlanOverview :proposal="proposal" :locale="locale" :messages="messages" />
        </div>

        <p
          v-if="staysChanged"
          class="mt-4 rounded-xl border border-amber-400/40 bg-amber-400/10 p-3 text-sm text-amber-200"
          role="alert"
        >
          {{ messages.staysChanged }}
        </p>

        <ol class="mt-6 space-y-4">
          <PlanDayCard
            v-for="(day, index) in proposal.days"
            :key="day.day"
            :day="day"
            :catalog="proposal.catalog"
            :locale="locale"
            :messages="messages"
            :has-night="index < proposal.days.length - 1"
          />
        </ol>

        <form class="glass-panel mt-6 rounded-2xl p-5" @submit.prevent="submitChange">
          <label for="plan-change" class="text-sm font-semibold">{{ messages.reviseLabel }}</label>
          <p v-if="proposal.changes.length" class="mt-1 text-xs text-slate-400">
            {{ messages.changesSoFar }}: {{ proposal.changes.join(' · ') }}
          </p>
          <textarea
            id="plan-change"
            v-model="change"
            rows="2"
            maxlength="500"
            class="mt-3 w-full resize-none rounded-xl border border-slate-700 bg-slate-900/70 p-3 text-sm text-slate-100 placeholder:text-slate-500"
            :placeholder="messages.revisePlaceholder"
          />
          <button
            type="submit"
            class="mt-3 flex w-full items-center justify-center gap-2 rounded-lg border border-emerald-400/60 py-2.5 text-sm font-semibold text-emerald-200 hover:bg-emerald-400/10 disabled:opacity-50"
            :disabled="!change.trim() || busy !== null"
          >
            <i :class="busy === 'revise' ? 'pi pi-spinner pi-spin' : 'pi pi-refresh'" aria-hidden="true" />
            {{ busy === 'revise' ? messages.revising : messages.revise }}
          </button>
        </form>
      </template>
    </main>

    <div v-if="proposal" class="fixed inset-x-0 bottom-0 z-30 border-t border-slate-800 bg-slate-950/90 backdrop-blur">
      <div class="mx-auto max-w-3xl px-4 py-3">
        <p v-if="errorMessage" class="mb-2 text-center text-sm text-rose-300" role="alert">{{ errorMessage }}</p>
        <button
          type="button"
          class="generate-button flex w-full items-center justify-center gap-2 rounded-xl py-3.5 text-sm font-semibold text-slate-900 disabled:opacity-50 sm:text-base"
          :disabled="!canBook || busy !== null"
          @click="accept"
        >
          <i :class="busy === 'accept' ? 'pi pi-spinner pi-spin' : 'pi pi-heart-fill'" aria-hidden="true" />
          {{ busy === 'accept' ? messages.booking : messages.book }}
        </button>
        <p class="mt-1.5 text-center text-xs text-slate-400">
          {{
            !canBook ? messages.nothingToBook : auth.isAuthenticated.value ? messages.bookHint : messages.signInToBook
          }}
        </p>
      </div>
    </div>
  </div>
</template>
