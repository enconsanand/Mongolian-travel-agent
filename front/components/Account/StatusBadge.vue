<script setup lang="ts">
const { status } = defineProps<{ status: string }>()
const { messages } = useAccountMessages()
const label = computed(() => messages.value.status[status as keyof typeof messages.value.status] ?? status)
const color = computed(() =>
  ['paid', 'confirmed', 'booked', 'completed'].includes(status)
    ? 'bg-success-soft text-success'
    : ['failed', 'cancelled', 'expired'].includes(status)
      ? 'bg-surface-muted text-ink-muted'
      : 'bg-accent-soft text-accent-ink'
)
</script>

<template>
  <span class="inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold" :class="color">{{ label }}</span>
</template>
