<script setup lang="ts">
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
    <PlannerHeader
      :locale="locale"
      :language-group-label="locale === 'mn' ? 'Хэл' : 'Language'"
      @set-locale="locale = $event"
    />

    <main class="mx-auto max-w-3xl px-4 pt-8 pb-10">
      <p v-if="loading && !proposal" class="text-ink-muted">{{ messages.loading }}</p>

      <section v-else-if="!proposal" class="panel p-6 text-center">
        <p class="text-ink-muted">{{ messages.notFound }}</p>
        <NuxtLink to="/" class="btn-primary mt-4 px-5 py-2.5">
          {{ messages.backToPlanner }}
        </NuxtLink>
      </section>

      <template v-else>
        <div class="flex items-baseline justify-between gap-3">
          <h1 class="text-2xl font-semibold sm:text-3xl">{{ messages.title }}</h1>
          <span class="shrink-0 text-xs text-ink-subtle">{{ messages.version }} {{ proposal.version }}</span>
        </div>

        <div class="mt-5">
          <PlanOverview :proposal="proposal" :locale="locale" :messages="messages" />
        </div>

        <p
          v-if="staysChanged"
          class="mt-4 rounded-control border border-accent/50 bg-warning-soft p-3 text-sm text-warning"
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

        <form class="panel mt-6 p-5" @submit.prevent="submitChange">
          <label for="plan-change" class="text-sm font-semibold">{{ messages.reviseLabel }}</label>
          <p v-if="proposal.changes.length" class="mt-1 text-xs text-ink-muted">
            {{ messages.changesSoFar }}: {{ proposal.changes.join(' · ') }}
          </p>
          <textarea
            id="plan-change"
            v-model="change"
            rows="2"
            maxlength="500"
            class="planner-field mt-3 text-sm"
            :placeholder="messages.revisePlaceholder"
          />
          <button
            type="submit"
            class="btn-secondary mt-3 w-full py-2.5 text-sm disabled:opacity-50"
            :disabled="!change.trim() || busy !== null"
          >
            <i :class="busy === 'revise' ? 'pi pi-spinner pi-spin' : 'pi pi-refresh'" aria-hidden="true" />
            {{ busy === 'revise' ? messages.revising : messages.revise }}
          </button>
        </form>
      </template>
    </main>

    <div v-if="proposal" class="sticky bottom-0 z-30 border-t border-line bg-surface">
      <div class="mx-auto max-w-3xl px-4 py-3">
        <p v-if="errorMessage" class="mb-2 text-center text-sm text-danger" role="alert">{{ errorMessage }}</p>
        <button
          type="button"
          class="btn-primary w-full py-3.5 text-sm disabled:opacity-50 sm:text-base"
          :disabled="!canBook || busy !== null"
          @click="accept"
        >
          <i :class="busy === 'accept' ? 'pi pi-spinner pi-spin' : 'pi pi-check'" aria-hidden="true" />
          {{ busy === 'accept' ? messages.booking : messages.book }}
        </button>
        <p class="mt-1.5 text-center text-xs text-ink-muted">
          {{
            !canBook ? messages.nothingToBook : auth.isAuthenticated.value ? messages.bookHint : messages.signInToBook
          }}
        </p>
      </div>
    </div>
  </div>
</template>
