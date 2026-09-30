<script setup lang="ts">
import type { PlanSearchStepStatus, PlanSearchStepView } from '~/types/trip-planner'

const { open, title, hint, closeLabel, cancelLabel, dialogLabel, steps, errorMessage, retryLabel } = defineProps<{
  open: boolean
  title: string
  hint: string
  closeLabel: string
  cancelLabel: string
  dialogLabel: string
  steps: PlanSearchStepView[]
  errorMessage: string | null
  retryLabel: string
}>()

const emit = defineEmits<{
  close: []
  retry: []
}>()

function stepIcon(status: PlanSearchStepStatus): string {
  if (status === 'complete') return 'pi pi-check-circle'
  if (status === 'active') return 'pi pi-spinner pi-spin'
  return 'pi pi-circle'
}

function stepClass(status: PlanSearchStepStatus): string {
  if (status === 'complete') return 'text-emerald-300'
  if (status === 'active') return 'animate-pulse text-cyan-300'
  return 'text-slate-500'
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape' && open) emit('close')
}

onMounted(() => {
  document.addEventListener('keydown', onKeydown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', onKeydown)
})
</script>

<template>
  <div
    v-if="open"
    class="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 p-4 backdrop-blur-sm"
    role="dialog"
    aria-modal="true"
    :aria-label="dialogLabel"
    @click.self="emit('close')"
  >
    <div class="glass-panel relative w-full max-w-md rounded-2xl p-6 shadow-2xl">
      <button
        type="button"
        class="absolute top-3 right-3 rounded-full p-2 text-slate-400 hover:bg-slate-800 hover:text-white"
        :aria-label="closeLabel"
        @click="emit('close')"
      >
        <i class="pi pi-times text-lg" aria-hidden="true" />
      </button>

      <div class="flex flex-col items-center text-center">
        <div class="relative h-16 w-16">
          <div class="absolute inset-0 rounded-full border-4 border-slate-800" />
          <div class="absolute inset-0 animate-spin rounded-full border-4 border-transparent border-t-emerald-400" />
          <i class="pi pi-compass absolute inset-0 m-auto text-xl text-cyan-300" aria-hidden="true" />
        </div>
        <h3 class="mt-4 text-lg font-semibold">{{ title }}</h3>
        <p class="mt-1 text-xs text-slate-400">{{ hint }}</p>
      </div>

      <p v-if="errorMessage" class="mt-6 rounded-lg bg-rose-500/10 p-3 text-center text-sm text-rose-300" role="alert">
        <i class="pi pi-exclamation-triangle mr-1" aria-hidden="true" />
        {{ errorMessage }}
      </p>

      <ul v-else class="mt-6 space-y-3 text-sm">
        <li v-for="step in steps" :key="step.id" class="flex items-center gap-3" :class="stepClass(step.status)">
          <i :class="stepIcon(step.status)" class="shrink-0 text-lg" aria-hidden="true" />
          {{ step.label }}
        </li>
      </ul>

      <button
        v-if="errorMessage"
        type="button"
        class="generate-button mt-6 w-full rounded-lg py-2.5 text-sm font-semibold text-slate-900"
        @click="emit('retry')"
      >
        {{ retryLabel }}
      </button>
      <button
        type="button"
        class="mt-3 w-full rounded-lg border border-slate-700 py-2.5 text-sm text-slate-300 hover:bg-slate-800"
        @click="emit('close')"
      >
        {{ cancelLabel }}
      </button>
    </div>
  </div>
</template>
